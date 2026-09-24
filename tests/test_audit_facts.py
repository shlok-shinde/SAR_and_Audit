import audit_trail as at
import typology as ty


def _index(case):
    d, flags = ty.analyse_case(case)
    return at.FactIndex(case.transactions, case.case_facts(), [f.to_dict() for f in flags],
                        d.to_dict())


def check(case, text):
    return at.check_sentence_facts(text, case.transactions, case.case_facts(), _index(case))


def test_exact_derived_and_dates(northgate_case):
    refs, unverified = check(northgate_case, "Between June 3 and June 6, 2024, NG-4471 received "
                                             "seven cash deposits totaling $68,150.00.")
    assert not unverified
    kinds = {(r.field_name, r.match_type) for r in refs}
    assert ("Inflow to NG-4471 (total)", "derived") in kinds
    assert ("Account", "exact") in kinds
    assert {r.field_value for r in refs if r.field_name == "Timestamp"} == {"2024-06-03",
                                                                           "2024-06-06"}


def test_wrong_figure_is_unverified_with_hint(northgate_case):
    _, unverified = check(northgate_case, "The account wired $67,000.00 abroad on June 9, 2024 "
                                          "to ZZ-99999.")
    values = {u.field_value: u.note for u in unverified}
    assert "closest in the case data: $67,500.00" in values["$67,000.00"]
    assert "2024-06-10" in values["2024-06-09"]            # closest real date (alert date)
    assert "ZZ-99999" in values


def test_rounded_mentions_are_approximate_but_cents_must_match(northgate_case):
    refs, unverified = check(northgate_case, "Deposits of approximately $68,000 were made.")
    assert not unverified and refs[0].match_type == "approximate"
    _, unverified = check(northgate_case, "Each deposit averaged $9,736.12.")
    assert unverified                                       # true average is $9,735.71


def test_regulatory_threshold_and_case_facts(northgate_case):
    refs, unverified = check(northgate_case, "Northgate Auto Parts LLC, a retail auto parts store "
                                             "since 2021-02-15, kept each deposit under the "
                                             "$10,000 threshold.")
    assert not unverified
    kinds = {r.match_type for r in refs}
    assert {"case_fact", "derived"} & kinds
    assert any(r.field_name == "Occupation / business" for r in refs)


def test_other_currencies_and_long_dates(ibm_samples):
    import case_input as ci
    case = ci.from_attempt(249)
    refs, unverified = check(case, "On September 9, 2022 the account paid 36,052.53 Rupee.")
    assert not unverified
    assert {r.match_type for r in refs} >= {"exact"}


def test_unverified_status_takes_precedence(northgate_case):
    sent = at.SentenceProvenance(0, "x", "What")
    sent.field_references = [at.FieldReference("Account", "NG-4471", "exact")]
    sent.chunk_attributions = ["c1"]
    assert at.grounding_status(sent) == "grounded"
    sent.unverified_values = [at.FieldReference("Amount", "$1.00", "unverified")]
    assert at.grounding_status(sent) == "unverified"


def test_legacy_audit_json_still_loads(northgate_case):
    """Audit JSON written before Milestone 5 has none of the new keys — it must still load.

    Built by stripping them from a record made here, so the test depends neither on
    audit_logs/ (git-ignored, rewritten by evaluate_narratives.py) nor on the IBM dataset.
    """
    NEW_RECORD_KEYS = ("red_flags", "detection", "case_facts", "generation_config", "case_source")
    NEW_SENTENCE_KEYS = ("rule_attributions", "unverified_values")

    d, flags = ty.analyse_case(northgate_case)
    text = ("### What (Suspicious Activity)\n\nNG-4471 received $68,150.00 in cash deposits and "
            "wired $38,000.00 to AE-77120.")
    current = at.build_audit_record("NG", 249, d.pattern, "m", 0, text, None, {},
                                    northgate_case.transactions,
                                    case_facts=northgate_case.case_facts(),
                                    detection=d.to_dict(), red_flags=flags).to_dict()
    legacy = {k: v for k, v in current.items() if k not in NEW_RECORD_KEYS}
    legacy["narrative_sentences"] = [
        {k: v for k, v in s.items() if k not in NEW_SENTENCE_KEYS}
        for s in legacy["narrative_sentences"]
    ]

    record = at.AuditRecord.from_dict(legacy)
    assert record.attempt_id == 249 and record.narrative_sentences
    assert record.red_flags == [] and record.case_source == "sample"
    assert all(s.rule_attributions == [] and s.unverified_values == []
               for s in record.narrative_sentences)
    assert at.generate_provenance_report(record)


def test_rebuild_is_deterministic(northgate_case):
    text = ("### What (Suspicious Activity)\n\nNG-4471 received $68,150.00 in cash and wired "
            "$38,000.00 to AE-77120.")
    d, flags = ty.analyse_case(northgate_case)
    rec = at.build_audit_record("NG", None, d.pattern, "m", 0, text, None, {},
                                northgate_case.transactions, case_facts=northgate_case.case_facts(),
                                detection=d.to_dict(), red_flags=flags)
    again = at.rebuild_audit_record(rec, text, None, {}, northgate_case.transactions)
    assert [at.grounding_status(s) for s in again.narrative_sentences] == \
           [at.grounding_status(s) for s in rec.narrative_sentences]
    assert again.model_used == "m + human edit"
    assert at.AuditRecord.from_dict(rec.to_dict()).red_flags == rec.red_flags


def test_count_claims(northgate_case):
    # gemma4:e2b wrote "nine cash deposits" for 7 cash deposits + 2 wires (live run)
    _, unverified = check(northgate_case, "NG-4471 received nine cash deposits from five "
                                          "different depositors and sent two wires.")
    assert [u.field_value for u in unverified] == ["nine cash deposits"]
    assert "7" in unverified[0].note
    _, unverified = check(northgate_case, "The activity involved 9 transactions across 8 "
                                          "accounts, including 7 deposits.")
    assert not unverified


def test_old_draft_count_error_is_caught(ibm_samples):
    import case_input as ci
    case = ci.from_attempt(285)             # case 003: 16 senders fan in to one account
    _, unverified = check(case, "The account received 16 inbound ACH transfers from 17 "
                                "separate senders.")
    assert [u.field_value for u in unverified] == ["17 separate senders"]
