"""Record the README demo video headlessly: no screen capture, no manual steps.

Drives the running app with Playwright's Chromium, draws captions and a pointer
into the page while it records, then cuts and encodes with ffmpeg:

    assets/demo.mp4   H.264, the full walkthrough (model wait sped up)
    assets/demo.gif   short preview for the README

Needs the app running (`streamlit run src/app.py --server.port 8502`), Ollama
with gemma4:e2b, Playwright (`pip install playwright && playwright install
chromium`) and ffmpeg. Nothing is written to the database: the case is
generated, reviewed and left unsaved.

    python scripts/record_demo.py [--url http://localhost:8502] [--out assets]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "generic_structuring.csv"
W, H = 1440, 900

OVERLAY_JS = r"""
() => {
  if (window.__demo) return;
  const font = "Geist, Inter, system-ui, sans-serif";
  const cap = document.createElement("div");
  Object.assign(cap.style, {position: "fixed", left: "calc(50% + 150px)", bottom: "26px",
    transform: "translateX(-50%)", zIndex: 2147483646, background: "rgba(14,14,14,.9)",
    color: "#F2F2F2", font: `500 20px/1.4 ${font}`, padding: "11px 22px", borderRadius: "12px",
    border: "1px solid rgba(255,255,255,.14)", maxWidth: "1040px", textAlign: "center",
    boxShadow: "0 10px 30px rgba(0,0,0,.5)", opacity: "0", transition: "opacity .3s",
    pointerEvents: "none"});
  const card = document.createElement("div");
  Object.assign(card.style, {position: "fixed", inset: "0", zIndex: 2147483647,
    background: "#1E1E1E", color: "#EDEDED", display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center", gap: "18px", fontFamily: font,
    opacity: "0", transition: "opacity .5s", pointerEvents: "none", textAlign: "center"});
  const ptr = document.createElement("div");
  ptr.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l16 9.5-7 1.6-3.8 6.4z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  Object.assign(ptr.style, {position: "fixed", left: "0", top: "0", zIndex: 2147483645,
    transform: "translate(720px, 450px)", transition: "transform .55s cubic-bezier(.3,.7,.2,1)",
    pointerEvents: "none", filter: "drop-shadow(0 2px 3px rgba(0,0,0,.5))"});
  const ring = document.createElement("div");
  Object.assign(ring.style, {position: "fixed", width: "34px", height: "34px", marginLeft: "-17px",
    marginTop: "-17px", borderRadius: "50%", border: "2px solid rgba(143,179,232,.95)",
    zIndex: 2147483644, opacity: "0", pointerEvents: "none"});
  document.body.append(cap, card, ptr, ring);
  window.__demo = {
    caption(t) { if (t) cap.innerHTML = t; cap.style.opacity = t ? "1" : "0"; },
    card(t, s) {
      if (t) card.innerHTML = `<div style="font:600 46px/1.15 ${font};letter-spacing:-.02em">${t}</div>` +
        `<div style="font:400 22px/1.5 ${font};color:#A3A3A3;max-width:900px">${s}</div>`;
      card.style.opacity = t ? "1" : "0";
    },
    move(x, y) { ptr.style.transform = `translate(${x - 4}px, ${y - 2}px)`; },
    tap(x, y) {
      ring.style.left = x + "px"; ring.style.top = y + "px";
      ring.animate([{opacity: 1, transform: "scale(.4)"}, {opacity: 0, transform: "scale(1.6)"}],
                   {duration: 500, easing: "ease-out"});
    },
  };
}
"""


class Demo:
    def __init__(self, page: Page):
        self.page = page
        self.t0 = time.monotonic()
        self.marks: dict[str, float] = {}

    def mark(self, name: str) -> None:
        self.marks[name] = time.monotonic() - self.t0

    def overlay(self) -> None:
        self.page.evaluate(OVERLAY_JS)

    def caption(self, text: str = "") -> None:
        self.overlay()
        self.page.evaluate("t => window.__demo.caption(t)", text)

    def card(self, title: str = "", sub: str = "") -> None:
        self.overlay()
        self.page.evaluate("([t, s]) => window.__demo.card(t, s)", [title, sub])

    def point(self, locator, pause: float = 0.6) -> tuple[float, float]:
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        x, y = box["x"] + min(box["width"] / 2, 60), box["y"] + box["height"] / 2
        self.overlay()
        self.page.evaluate("([x, y]) => window.__demo.move(x, y)", [x, y])
        self.page.mouse.move(x, y)
        time.sleep(pause)
        return x, y

    def click(self, locator, pause: float = 0.6) -> None:
        x, y = self.point(locator, pause)
        self.page.evaluate("([x, y]) => window.__demo.tap(x, y)", [x, y])
        locator.click()

    def type_into(self, locator, text: str, delay: int = 35) -> None:
        self.click(locator, 0.4)
        locator.press_sequentially(text, delay=delay)
        locator.press("Tab")

    def select(self, label: str, option: str) -> None:
        self.click(self.page.get_by_label(label, exact=True), 0.4)
        time.sleep(0.4)
        self.click(self.page.get_by_role("option", name=option, exact=True), 0.35)

    @staticmethod
    def wait(seconds: float) -> None:
        time.sleep(seconds)


def pick_amount(text: str) -> tuple[str, str] | None:
    """An amount the draft states in two places (else once), and a plausible typo of it.

    Stating it twice shows the stale-value note on the other sentence. Amounts are
    compared by value ("$68,150" and "$68,150.00" are the same); the $10,000
    reporting threshold is regulatory, not case data, so it is never picked.
    """
    raw = re.findall(r"\$\d{1,3}(?:,\d{3})+(?:\.\d{2})?", text)
    value = lambda a: float(a[1:].replace(",", ""))
    found = [a for a in raw if value(a) != 10_000]
    if not found:
        return None
    counts = {}
    for a in found:
        counts[value(a)] = counts.get(value(a), 0) + 1
    repeated = [a for a in found if counts[value(a)] > 1]
    amount = (repeated or found)[0]
    print(f"amount to edit: {amount} (stated {counts[value(amount)]}x)", flush=True)
    wrong = "$" + str((int(amount[1]) + 2) % 10 or 9) + amount[2:]
    return amount, wrong


def record(url: str, video_dir: Path) -> tuple[Path, dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                                  record_video_dir=str(video_dir),
                                  record_video_size={"width": W, "height": H})
        page = ctx.new_page()
        d = Demo(page)
        page.goto(url)
        page.get_by_text("Draft SAR narratives you can audit").wait_for(timeout=90_000)
        d.card("SAR Narrative Generator",
               "Drafts Suspicious Activity Report narratives with a local model,<br>"
               "and checks every sentence against the case data")
        d.mark("start")
        d.wait(4)
        d.card()
        d.wait(0.6)

        # ── 1. Case intake ──
        d.caption("An analyst starts a case from their own bank export")
        d.wait(1.5)
        d.click(page.get_by_test_id("stSidebar").get_by_role("button", name="Start a new case"))
        d.wait(1.5)
        d.point(page.get_by_text("Upload transactions (CSV or Excel)"))
        page.locator('input[type="file"]').set_input_files(str(FIXTURE))
        d.wait(2.5)
        d.caption("Columns are recognised and mapped; <b>Flagged</b> rows are the activity under review")
        d.point(page.get_by_text("Flagged", exact=True).first, 0.3)
        d.wait(3.5)

        d.click(page.get_by_role("tab", name="2 · Subject & alert"))
        d.caption("Add the customer profile: the baseline examiners look for")
        d.wait(1)
        d.type_into(page.get_by_label("Name", exact=True), "Northgate Auto Parts LLC")
        d.select("Type", "Business")
        d.type_into(page.get_by_label("Occupation / nature of business"), "Retail auto parts store")
        d.type_into(page.get_by_label("Country", exact=True), "US", delay=80)
        d.type_into(page.get_by_label("Expected monthly incoming volume ($)"), "40000", delay=60)
        d.select("Source", "Transaction monitoring alert")
        desc = page.get_by_label("What triggered the review")
        d.click(desc, 0.4)
        desc.fill("Multiple cash deposits just below $10,000 from different depositors, "
                  "followed by international wires.")
        desc.press("Tab")
        d.wait(1.5)

        d.click(page.get_by_role("tab", name="3 · Investigation"))
        d.caption("…and the investigation: steps taken, findings, explanations ruled out")
        d.wait(1)
        for step in ("Reviewed KYC / customer due diligence file",
                     "Reviewed account activity for the lookback period",
                     "Searched for prior SARs on the subject",
                     "Contacted the customer for an explanation"):
            d.click(page.get_by_role("button", name=step), 0.35)
            d.wait(0.5)
        findings = page.get_by_label("Findings", exact=True)
        d.click(findings, 0.4)
        findings.fill("The owner said the cash came from customers paying for bulk orders but "
                      "provided no invoices. No prior SARs were found.")
        ruled = page.get_by_label("Explanations considered and ruled out")
        d.click(ruled, 0.4)
        ruled.fill("Seasonal sales: May 2024 card settlements averaged about $1,900 per deposit "
                   "with no cash activity.")
        ruled.press("Tab")
        d.wait(1.5)

        # ── 2. Rules ──
        d.click(page.get_by_role("tab", name="4 · Review & generate"))
        d.caption("Rules, not the model, detect the typology and the red flags, with evidence")
        d.wait(1.5)
        d.point(page.get_by_text("Amounts just below the $10,000 reporting threshold"))
        d.wait(3.5)
        d.caption("The money flow, drawn from the transactions")
        d.point(page.get_by_text("Funds flow", exact=True))
        page.mouse.wheel(0, 560)
        d.wait(3.5)

        # ── 3. Generation (sped up in the edit) ──
        gen = page.get_by_role("button", name="Generate draft and audit trail")
        d.caption("Draft it")
        d.click(gen)
        d.mark("gen_start")
        d.caption("Drafting locally with gemma4:e2b in Ollama: nothing leaves the machine "
                  "<span style='color:#A3A3A3'>(sped up)</span>")
        page.get_by_text("Draft narrative", exact=True).wait_for(timeout=400_000)
        d.wait(1.5)
        d.mark("gen_end")

        # ── 4. Review ──
        d.caption("Draft and audit trail side by side: every sentence is checked against the case data")
        d.wait(3.5)
        d.click(page.locator("[data-hl]").first)
        d.caption("Highlight sourcing: green cites case data and analysis, amber one of them, red neither")
        d.wait(3.5)
        sentence = page.locator(".s.grounded").nth(1)
        d.click(sentence)
        d.caption("Click a sentence to see its evidence: transaction fields, regulations, rule findings")
        d.wait(4.5)

        # ── 5. Edit → live re-audit ──
        d.click(page.locator("button", has_text=re.compile(r"^\s*Markdown\s*$")))
        d.wait(1.5)
        ta = page.locator('textarea[aria-label="Narrative (Markdown)"]')
        picked = pick_amount(ta.input_value())
        if picked:
            amount, wrong = picked
            d.caption(f"Now change a figure: {amount} → {wrong}")
            page.evaluate(r"""(needle) => {
              const ta = document.querySelector('textarea[aria-label="Narrative (Markdown)"]');
              const i = ta.value.indexOf(needle);
              const cs = getComputedStyle(ta), ctx = document.createElement("canvas").getContext("2d");
              ctx.font = `${cs.fontSize} ${cs.fontFamily}`;
              const cpl = Math.max(20, Math.floor((ta.clientWidth - 24) / ctx.measureText("m").width));
              const rows = ta.value.slice(0, i).split("\n")
                .reduce((n, l) => n + Math.max(1, Math.ceil(l.length / cpl)), 0);
              const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.5;
              ta.focus(); ta.setSelectionRange(i, i + needle.length);
              ta.scrollTop = Math.max(0, rows * lh - ta.clientHeight / 2);
            }""", amount)
            box = ta.bounding_box()
            page.evaluate("([x, y]) => window.__demo.move(x, y)",
                          [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2])
            d.wait(1.5)
            page.keyboard.type(wrong, delay=110)
            d.wait(0.6)
            page.keyboard.press("Control+Enter")
            d.mark("edit_start")
            d.caption("The audit re-runs on the edited text: rules only, no model call")
            edited = page.locator(".card").filter(has_text=wrong.replace("$", "")).first
            edited.locator(".tag").wait_for(timeout=120_000)
            d.mark("edit_end")
            d.wait(0.8)
            d.caption(f"The edited sentence is now <b>Unverified</b>: {wrong} is not in the case data")
            d.point(edited)
            d.wait(4.5)
            stale = page.locator(".card").filter(has=page.locator(".note")).first
            if stale.count():
                d.caption("…and the other sentence that still states the old amount is pointed out for review")
                d.point(stale)
                d.wait(4.5)

        # ── 6. Decide and export ──
        page.mouse.wheel(0, -3000)
        d.wait(0.8)
        d.click(page.locator(".st-key-decide-pop button").first)
        d.caption("Decide SAR or No SAR, with a rationale; a second person must approve")
        d.wait(4)
        page.keyboard.press("Escape")
        d.wait(0.6)
        d.click(page.locator(".st-key-export-pop button").first)
        d.caption("Export the FinCEN narrative text, a printable case file and the audit record")
        d.wait(4)
        page.keyboard.press("Escape")
        d.caption()
        d.card("Runs entirely on your machine",
               "Ollama · ChromaDB · PostgreSQL · Streamlit<br>No case data leaves the environment")
        d.wait(4)
        d.mark("end")
        video = Path(page.video.path())
        ctx.close()
        browser.close()
    return video, d.marks


def encode(raw: Path, marks: dict, out: Path) -> None:
    """Cut the recording, speed up the waits, write MP4 + GIF preview."""
    start, end = max(0.0, marks["start"] - 0.3), marks["end"]
    fast = [(marks["gen_start"] + 1.8, marks["gen_end"] - 0.5, 3.0)]
    if "edit_end" in marks and marks["edit_end"] - marks["edit_start"] > 3:
        fast.append((marks["edit_start"] + 0.8, marks["edit_end"] - 0.3, 1.5))
    parts, cursor = [], start
    for a, b, target in fast:
        parts.append((cursor, a, 1.0))
        parts.append((a, b, max(1.0, (b - a) / target)))
        cursor = b
    parts.append((cursor, end, 1.0))
    chains = [f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=(PTS-STARTPTS)/{k:.3f}[v{i}]"
              for i, (a, b, k) in enumerate(parts)]
    graph = ";".join(chains) + ";" + "".join(f"[v{i}]" for i in range(len(parts))) + \
        f"concat=n={len(parts)}:v=1:a=0,fps=30,format=yuv420p[out]"
    out.mkdir(parents=True, exist_ok=True)
    mp4, gif = out / "demo.mp4", out / "demo.gif"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-filter_complex", graph,
                    "-map", "[out]", "-c:v", "libx264", "-preset", "slow", "-crf", "22",
                    "-movflags", "+faststart", str(mp4)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf",
                    "setpts=PTS/1.6,fps=7,scale=880:-1:flags=lanczos,split[a][b];"
                    "[a]palettegen=max_colors=96:stats_mode=diff[p];"
                    "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
                    str(gif)], check=True)
    print(json.dumps({"parts": parts, "mp4": str(mp4), "gif": str(gif)}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8502")
    ap.add_argument("--out", default=str(ROOT / "assets"))
    ap.add_argument("--keep-raw", default="")
    args = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="sar-demo-"))
    raw, marks = record(args.url, tmp)
    print(json.dumps(marks, indent=1))
    if args.keep_raw:
        shutil.copy(raw, args.keep_raw)
    encode(raw, marks, Path(args.out))
    shutil.rmtree(tmp, ignore_errors=True)
