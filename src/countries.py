"""Country names for the fact-check: which jurisdictions a narrative names, and
which ones the case data supports.

A narrative that says "transfers to India" when no transaction, bank, currency or
case fact involves India is stating something the case can't back up. The IBM
data has no country column; countries appear in bank names ("China Bank #6"),
so every text field of the case is searched, not only the country columns.

Deliberately not matched: the abbreviations "US" / "U.S." (mostly adjectives,
"U.S. financial system", "US Dollar") and demonyms ("Chinese", "German").
"""
from __future__ import annotations

import re

# ISO 3166-1 alpha-2 → canonical name, then aliases. UN members plus the
# territories that matter in AML work (offshore centres, FATF-listed).
_TABLE = """
AF Afghanistan|AL Albania|DZ Algeria|AD Andorra|AO Angola|AG Antigua and Barbuda
AR Argentina|AM Armenia|AU Australia|AT Austria|AZ Azerbaijan|BS Bahamas;The Bahamas
BH Bahrain|BD Bangladesh|BB Barbados|BY Belarus|BE Belgium|BZ Belize|BJ Benin|BT Bhutan
BO Bolivia|BA Bosnia and Herzegovina;Bosnia|BW Botswana|BR Brazil|BN Brunei|BG Bulgaria
BF Burkina Faso|BI Burundi|CV Cabo Verde;Cape Verde|KH Cambodia|CM Cameroon|CA Canada
CF Central African Republic|TD Chad|CL Chile|CN China;People's Republic of China;PRC
CO Colombia|KM Comoros|CG Republic of the Congo;Congo-Brazzaville
CD Democratic Republic of the Congo;DRC;DR Congo;Congo-Kinshasa|CR Costa Rica
CI Côte d'Ivoire;Cote d'Ivoire;Ivory Coast|HR Croatia|CU Cuba|CY Cyprus
CZ Czech Republic;Czechia|DK Denmark|DJ Djibouti|DM Dominica|DO Dominican Republic
EC Ecuador|EG Egypt|SV El Salvador|GQ Equatorial Guinea|ER Eritrea|EE Estonia
SZ Eswatini;Swaziland|ET Ethiopia|FJ Fiji|FI Finland|FR France|GA Gabon|GM Gambia;The Gambia
GE Georgia|DE Germany|GH Ghana|GR Greece|GD Grenada|GT Guatemala|GN Guinea
GW Guinea-Bissau|GY Guyana|HT Haiti|HN Honduras|HU Hungary|IS Iceland|IN India
ID Indonesia|IR Iran|IQ Iraq|IE Ireland|IL Israel|IT Italy|JM Jamaica|JP Japan|JO Jordan
KZ Kazakhstan|KE Kenya|KI Kiribati|KP North Korea;DPRK|KR South Korea;Republic of Korea
KW Kuwait|KG Kyrgyzstan|LA Laos;Lao PDR|LV Latvia|LB Lebanon|LS Lesotho|LR Liberia|LY Libya
LI Liechtenstein|LT Lithuania|LU Luxembourg|MG Madagascar|MW Malawi|MY Malaysia|MV Maldives
ML Mali|MT Malta|MH Marshall Islands|MR Mauritania|MU Mauritius|MX Mexico|FM Micronesia
MD Moldova|MC Monaco|MN Mongolia|ME Montenegro|MA Morocco|MZ Mozambique|MM Myanmar;Burma
NA Namibia|NR Nauru|NP Nepal|NL Netherlands;The Netherlands;Holland|NZ New Zealand
NI Nicaragua|NE Niger|NG Nigeria|MK North Macedonia;Macedonia|NO Norway|OM Oman
PK Pakistan|PW Palau|PS Palestine|PA Panama|PG Papua New Guinea|PY Paraguay|PE Peru
PH Philippines;The Philippines|PL Poland|PT Portugal|QA Qatar|RO Romania
RU Russia;Russian Federation|RW Rwanda|KN Saint Kitts and Nevis|LC Saint Lucia
VC Saint Vincent and the Grenadines|WS Samoa|SM San Marino|ST Sao Tome and Principe
SA Saudi Arabia|SN Senegal|RS Serbia|SC Seychelles|SL Sierra Leone|SG Singapore
SK Slovakia|SI Slovenia|SB Solomon Islands|SO Somalia|ZA South Africa|SS South Sudan
ES Spain|LK Sri Lanka|SD Sudan|SR Suriname|SE Sweden|CH Switzerland|SY Syria|TW Taiwan
TJ Tajikistan|TZ Tanzania|TH Thailand|TL Timor-Leste;East Timor|TG Togo|TO Tonga
TT Trinidad and Tobago|TN Tunisia|TR Turkey;Türkiye|TM Turkmenistan|TV Tuvalu|UG Uganda
UA Ukraine|AE United Arab Emirates;UAE;U.A.E.|GB United Kingdom;UK;U.K.;Great Britain;Britain;England;Scotland;Wales;Northern Ireland
US United States;United States of America;USA;U.S.A.|UY Uruguay|UZ Uzbekistan|VU Vanuatu
VA Vatican City;Holy See|VE Venezuela|VN Vietnam;Viet Nam|YE Yemen|ZM Zambia|ZW Zimbabwe
HK Hong Kong|MO Macau;Macao|KY Cayman Islands|VG British Virgin Islands;BVI|BM Bermuda
GI Gibraltar|JE Jersey|GG Guernsey|IM Isle of Man|PR Puerto Rico|CW Curaçao;Curacao
AW Aruba|TC Turks and Caicos Islands|AI Anguilla
"""

COUNTRIES: dict[str, tuple[str, ...]] = {}
for _entry in re.split(r"[|\n]", _TABLE):
    if _entry.strip():
        _code, _names = _entry.strip().split(" ", 1)
        COUNTRIES[_code] = tuple(n.strip() for n in _names.split(";"))

_BY_NAME = {n.lower(): names[0] for names in COUNTRIES.values() for n in names}
_BY_CODE = {code: names[0] for code, names in COUNTRIES.items()}

# Longest first, so "Papua New Guinea" wins over "Guinea" and "South Sudan" over "Sudan".
# Case-sensitive: "Chad" and "Turkey" the country, not the name or the bird.
_ALL_NAMES = sorted({n for names in COUNTRIES.values() for n in names}, key=len, reverse=True)
# "New Mexico" / "New Jersey" are US states, not the countries.
_MENTION = re.compile(r"(?<![\w.])(?<!New )(?:" + "|".join(re.escape(n) for n in _ALL_NAMES) + r")(?![\w-])")

# Currencies issued by a single country (the case's currency names, case_input.CURRENCY_CODES).
CURRENCY_COUNTRY = {
    "US Dollar": "United States", "Yuan": "China", "Rupee": "India", "Yen": "Japan",
    "UK Pound": "United Kingdom", "Ruble": "Russia", "Brazil Real": "Brazil",
    "Mexican Peso": "Mexico", "Canadian Dollar": "Canada", "Australian Dollar": "Australia",
    "Swiss Franc": "Switzerland", "Saudi Riyal": "Saudi Arabia", "Shekel": "Israel",
}


def canonical_country(value) -> str | None:
    """A country column value (ISO code or name) → canonical name."""
    v = str(value or "").strip()
    if not v:
        return None
    if len(v) == 2 and v.upper() in _BY_CODE:
        return _BY_CODE[v.upper()]
    return _BY_NAME.get(v.lower())


def country_mentions(text: str) -> list[tuple[str, tuple[int, int], str]]:
    """Countries named in `text`: (canonical name, span, as written)."""
    return [(_BY_NAME[m.group(0).lower()], m.span(), m.group(0))
            for m in _MENTION.finditer(text or "")]
