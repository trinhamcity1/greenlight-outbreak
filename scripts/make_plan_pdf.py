"""Build docs/outbreak-synth-plan.pdf, the plain-language plan for GreenLight."""
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", F + "DejaVuSans-Bold.ttf"))
registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")

INK, MUTED, ACCENT, SOFT, LINE = (colors.HexColor(c) for c in ("#1f2328", "#57606a", "#0b6e4f", "#eef6f2", "#d0d7de"))

s_title = ParagraphStyle("t", fontName="Sans-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=4)
s_sub = ParagraphStyle("s", fontName="Sans", fontSize=10, leading=14, textColor=MUTED, spaceAfter=14)
s_h = ParagraphStyle("h", fontName="Sans-Bold", fontSize=13, leading=17, textColor=ACCENT, spaceBefore=10, spaceAfter=4)
s_body = ParagraphStyle("b", fontName="Sans", fontSize=9.3, leading=12.8, textColor=INK, spaceAfter=5, alignment=TA_LEFT)
s_bul = ParagraphStyle("u", parent=s_body, leftIndent=12, bulletIndent=2, spaceAfter=3)
s_cell = ParagraphStyle("c", fontName="Sans", fontSize=8.6, leading=11.5, textColor=INK)
s_cellb = ParagraphStyle("cb", parent=s_cell, fontName="Sans-Bold")
s_note = ParagraphStyle("n", parent=s_body, fontSize=8.5, leading=12, textColor=MUTED)

P = lambda t, s=s_body: Paragraph(t, s)
B = lambda t: Paragraph(t, s_bul, bulletText="•")


def table(rows, widths, header=True):
    data = [[Paragraph(c, s_cellb if (header and i == 0) else s_cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    st = [("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), SOFT))
    t.setStyle(TableStyle(st))
    return t


def flow():
    """Daily loop: fob rows -> Kinship Vote -> Two-Part Recipe -> Fresh-Days Check -> green light -> Synth."""
    w, h = 7.0 * inch, 2.0 * inch
    d = Drawing(w, h)
    boxes = [("fob's data", "so far"), ("Kinship", "Vote"), ("Two-Part", "Recipe"), ("Lab-Label", "Fallback?"),
             ("Green", "Light?"), ("Synth", "Release")]
    bw, bh, gap, y = 0.95 * inch, 0.62 * inch, 0.24 * inch, 0.85 * inch
    xs = [i * (bw + gap) for i in range(len(boxes))]
    for i, (a, b) in enumerate(boxes):
        fill = SOFT if i in (1, 2, 3, 4) else colors.white
        d.add(Rect(xs[i], y, bw, bh, rx=6, ry=6, fillColor=fill, strokeColor=ACCENT, strokeWidth=1))
        d.add(String(xs[i] + bw / 2, y + bh / 2 + 3, a, fontName="Sans-Bold", fontSize=8.5, textAnchor="middle", fillColor=INK))
        d.add(String(xs[i] + bw / 2, y + bh / 2 - 9, b, fontName="Sans", fontSize=8.5, textAnchor="middle", fillColor=INK))
        if i:
            x0, x1, ym = xs[i - 1] + bw, xs[i], y + bh / 2
            d.add(Line(x0 + 2, ym, x1 - 4, ym, strokeColor=MUTED, strokeWidth=1))
            d.add(Polygon([x1 - 2, ym, x1 - 8, ym + 3.5, x1 - 8, ym - 3.5], fillColor=MUTED, strokeColor=MUTED))
    # Outbreak Atlas feeding the Kinship Vote
    ax = xs[1]
    d.add(Rect(ax, 0.05 * inch, bw * 3 + gap * 2, 0.42 * inch, rx=6, ry=6, fillColor=colors.white, strokeColor=MUTED, strokeDashArray=[3, 2]))
    d.add(String(ax + (bw * 3 + gap * 2) / 2, 0.21 * inch, "Atlas (past outbreaks or past vaccines)", fontName="Sans", fontSize=8.5, textAnchor="middle", fillColor=MUTED))
    d.add(Line(ax + bw / 2, 0.47 * inch, ax + bw / 2, y - 3, strokeColor=MUTED))
    d.add(Polygon([ax + bw / 2, y - 1, ax + bw / 2 - 3.5, y - 7, ax + bw / 2 + 3.5, y - 7], fillColor=MUTED, strokeColor=MUTED))
    # "not yet" loop back from Green Light to fob's rows (tomorrow)
    gx = xs[4] + bw / 2
    top = y + bh + 0.26 * inch
    d.add(Line(gx, y + bh, gx, top, strokeColor=MUTED))
    d.add(Line(gx, top, xs[0] + bw / 2, top, strokeColor=MUTED))
    d.add(Line(xs[0] + bw / 2, top, xs[0] + bw / 2, y + bh + 4, strokeColor=MUTED))
    d.add(Polygon([xs[0] + bw / 2, y + bh + 1, xs[0] + bw / 2 - 3.5, y + bh + 7, xs[0] + bw / 2 + 3.5, y + bh + 7], fillColor=MUTED, strokeColor=MUTED))
    d.add(String((gx + xs[0] + bw / 2) / 2, top + 4, "not yet → wait for more data", fontName="Sans", fontSize=8, textAnchor="middle", fillColor=MUTED))
    return d


def footer(c, doc):
    c.saveState()
    c.setFont("Sans", 7.5)
    c.setFillColor(MUTED)
    c.drawString(0.75 * inch, 0.5 * inch, "GreenLight · plan v3.2 · 2026-10-07")
    c.drawRightString(7.75 * inch, 0.5 * inch, f"Page {doc.page}")
    c.restoreState()


story = [
    P("GreenLight", s_title),
    P("Plan v3.2: what has been built and learned (Case Study 1, early outbreaks), and what comes next. "
      "GreenLight studies past outbreaks, follows a new one day by day, says when it understands it, and only then "
      "releases synthetic patient data.", s_sub),

    P("1. The idea in one paragraph", s_h),
    P("Something new appears, which we call <b>fob</b>. In Case Study 1 it is a new disease outbreak; in Case Study 2 "
      "(planned) it is a new vaccine. At first there are only a few records. GreenLight combines them with what it learned from "
      "similar past outbreaks, keeps checking itself, and turns on a <b>green light</b> when its understanding is good "
      "enough. Only then does it generate synthetic patients. The contribution is the <b>method</b>: deciding what to learn "
      "from, how much to borrow and for how long, when it is ready, and explaining every decision."),

    P("2. Data used so far (all public, all cited in the repository)", s_h),
    table([
        ["Source", "What", "Used for"],
        ["Brazil SIVEP-Gripe (Ministry of Health, CC-BY)", "24 outbreaks 2009–2022: H1N1 2009, flu and other-virus seasons, "
         "COVID-19 2020–22; about 2.15 million hospitalised patients", "Outbreak Atlas; all replays"],
        ["Mexico SISVER (Secretaría de Salud, free-use terms)", "COVID-19 2020 and 2021: 326,886 and 297,685 hospitalised patients",
         "Out-of-country test, settings fixed from Brazil"],
        ["Kenema Ebola 2014 (Zenodo); H7N9 China 2013, MERS Korea 2015 (R package outbreaks, GPL)",
         "83, 74 and 162 patients; age and sex only", "Vote-only test on very different pathogens"],
    ], [2.3 * inch, 3.0 * inch, 1.7 * inch]),

    P("3. The parts of GreenLight, as built", s_h),
    table([
        ["Name", "What it does now", "Status"],
        ["<b>Outbreak Atlas</b>", "Past outbreaks mapped to shared fields (age, sex, race, state, 6 symptoms, 10 conditions). "
         "Fields a form never collected are 'missing'.", "Built (Brazil + Mexico)"],
        ["<b>Kinship Vote</b>", "Each past outbreak predicts fob's new patients each week (patient mix + who dies, with fob's own "
         "death rate). Better predictions earn more votes. It compares only fields fob's form collects, and each pathogen "
         "group starts with an equal share of the vote.", "Built, tested"],
        ["<b>Stranger Flag</b>", "A 'none of the above' candidate learning from fob alone. Winning early means fob is new.", "Built, tested"],
        ["<b>Lab-Label Fallback</b>", "New: if the lab says fob's pathogen group has no earlier member in the Atlas, GreenLight uses an "
         "age-trend model until 20 deaths have been scored, then borrows.", "Built, tested"],
        ["<b>Two-Part Recipe</b>", "Profile Model (who is hospitalised) + Severity Model (who dies). Severity: logistic regression "
         "with priors from voted relatives.", "Built"],
        ["<b>Handover Rule</b>", "Borrowing strength 10 × (1 − Stranger share). Never borrowed: overall death rate, geography. "
         "A minimum restraint pulls towards 'no effect' (not towards relatives) so rare groups stay sensible.", "Built, tuned on Brazil"],
        ["<b>Fresh-Days Check</b>", "Scores recipes on fob's newest unseen patients. As a recipe switcher it did not help "
         "(see section 5); kept as evidence in the Glass Box Report.", "Built; no gain"],
        ["<b>green light</b>", "At least 10 deaths with a known outcome, and GreenLight's risk ranking of fob's patients stable (rank correlation of 0.99 or more vs 8 days "
         "earlier) on two checks in a row, and not on the fallback.", "Built, tested"],
        ["<b>Synth Release</b>", "After the green light: synthetic patients from the Two-Part Recipe. Symptoms and conditions come "
         "from a <b>Dependency Chain</b> (each given age band, sex and the fields before it). Every row is labelled synthetic with provenance.", "Built, tested"],
        ["<b>Glass Box Report</b>", "An HTML page per outbreak and day: green light conditions, Kinship Vote, risk table (odds "
         "ratios, relatives' values, share still borrowed), recent evidence, synthetic vs real. Hindsight scores are kept separate.", "Built"],
        ["<b>OutbreakReplay</b>", "Every outbreak replayed day by day as if new, hiding the future, to test all of the above. "
         "A patient's outcome is used only from the day it was recorded (v3.2).", "Built"],
    ], [1.35 * inch, 4.25 * inch, 1.4 * inch]),

    Spacer(1, 4),
    KeepTogether([P("4. One step in the life of GreenLight", s_h), Spacer(1, 4), flow(),
                  P("Each day new fob data arrives. GreenLight updates the Kinship Vote, applies the Lab-Label Fallback if needed, refits the "
                    "Two-Part Recipe with the Handover Rule, and checks the green light. 'Not yet' means wait for more data.", s_note)]),

    P("5. What we learned (OutbreakReplay)", s_h),
    table([
        ["Question", "Answer from the data"],
        ["How long does real data alone take?", "COVID-19 Brazil 2020: about 33 days to come within 0.02 AUC of the best possible. "
         "H1N1 2009: 56 days. In the first 3 weeks there is too little data to train at all."],
        ["Does the Kinship Vote find the right group?", "Right group in 90% of 23 Brazil outbreaks in weeks 1–4 and 95% "
         "from week 8. When it is 95% sure, it is right 98% of the time."],
        ["Does the Stranger Flag catch a new disease?", "COVID-19 flagged in week 4 in Brazil (3,538 patients) and week 4 in "
         "Mexico (1,262). It needs several hundred patients: it never fires in outbreaks under 200 patients."],
        ["Does borrowing help?", "Familiar flu and other-virus seasons: at the plateau from day 0, while real data alone usually "
         "could not even train a model in 90 days. COVID-19 Brazil: no gain once outcomes count only when known "
         "(plateau day 36 for both GreenLight and real data alone; it looked like 28 vs 34 before this fix)."],
        ["Is it safe for a new disease?", "Without the Lab-Label Fallback, GreenLight was worse than 'rank by age' in COVID's first 3 weeks. "
         "With it, never worse in Brazil's new-pathogen outbreaks. In Mexico it was below age-only for 34 of 90 days after the fallback ended, "
         "as was real data alone."],
        ["Is the green light honest?", "Brazil, outcomes counted only when known: the old rule (20 deaths, 0.98) gave 2 false greens, so it was "
         "re-chosen leave-one-outbreak-out: 22 of 23 green, 1 false, median day 37; fixed at (10, 0.99): COVID-19 green on day 54. Mexico (old timing): "
         "honest in both years (days 48 and 18)."],
        ["Is the synthetic data useful?", "Across 22 Brazil outbreaks (outcomes counted only when known) a model trained on GreenLight synthetic data scores AUC 0.796, against "
         "0.730 for the real records GreenLight had. For outbreaks with under 1,000 real records: 0.718 → 0.804 when added."],
        ["Does it beat standard borrowing? (Exp. 15)", "Lowest gap to the best possible model of 9 baselines (pooled past, "
         "stacking, fine-tuning, meta-analytic and robust priors, empirical Bayes, source averaging, a MetaPred-style meta-learner, "
         "equal-weight kin). But against fine-tuning or stacking the margin is small and not statistically clear; the Kinship Vote "
         "adds a small, consistent gain over equal weights. The main safety gain is the Lab-Label Fallback: without it every "
         "baseline falls below 'rank by age' for COVID's first weeks."],
        ["Do sample-size rules do the green light's job?", "No. Riley's minimum sample size needs 2,100–7,100 patients with a known "
         "outcome and turns on in only 5 of 23 outbreaks (3 COVID, 2 large flu seasons); never in other-virus seasons, where GreenLight is good from day 0."],
        ["Does it beat standard generators? (Exp. 16)", "On the same records and day: GreenLight synthetic 0.796 AUC; ARF 0.770, TVAE 0.704, "
         "bootstrap 0.679, Bayesian network 0.676, CTGAN 0.613. The gain comes from borrowed knowledge, so it shrinks where fob's own "
         "data are plentiful (COVID, flu 2022)."],
        ["Is it realistic?", "Synthetic patients match the real ones within about 0.4 points of death rate. With the Dependency Chain, "
         "links between symptoms and conditions are as close to later patients as the real data's own drift."],
    ], [2.0 * inch, 5.0 * inch]),
    Spacer(1, 4),
    P("<b>The key lesson:</b> synthetic data from GreenLight carries GreenLight's understanding, no more and no less. It helps exactly when "
      "real data are scarce and borrowed knowledge is good. The green light decides when that is the case."),

    P("6. What did not work (kept in the record)", s_h),
    B("Borrowing from all past outbreaks equally: it learned only 'older patients die more' (no better than ranking by age)."),
    B("Fresh-Days Check as a recipe switcher: it switched on a handful of patients and made early weeks worse. With a 100-death "
      "minimum it equals plain borrowing."),
    B("'Borrow only what relatives agree on' and 'borrow only the age pattern': both worse than plain borrowing."),
    B("Outcome-based alarms for a new disease: there are almost no deaths in the first weeks, so they come too late."),
    B("A misleading relative from the same group (H1N1 before the 2013 flu season) is still not caught early."),

    P("7. Open decisions", s_h),
    B("<b>Decided (2026-10-07): equal start per group in the Kinship Vote.</b> Before, groups with more past outbreaks started ahead "
      "(flu 43%, COVID 20% before any data). With an equal start per group, Brazil results are the same or slightly better (days below "
      "'rank by age' 64 → 50), and MERS leans 66% COVID-like instead of 47%."),
    B("<b>When to leave the Lab-Label Fallback.</b> 20 deaths is a judgement call based on 3 new-pathogen outbreaks."),
    B("<b>More truly new diseases.</b> The Atlas has about 4 distinct diseases and one new pathogen (COVID-19, in 2 countries). "
      "Trust claims rest on that."),

    P("8. Case Study 2: vaccine side-effect signals (planned, next)", s_h),
    P("Same method, different fob: a new vaccine rollout, week by week. Question: can GreenLight confirm real side-effect signals "
      "earlier than standard safety statistics, with no more false alarms, and point to the groups at risk? Replay cases "
      "(dates to verify): myocarditis after mRNA vaccines; blood clots after viral-vector vaccines; narcolepsy after Pandemrix; "
      "intussusception after RotaShield. First step: check what public data can be downloaded (VAERS; Brazil's adverse-event "
      "reports), its licence and fields."),

    P("9. Limits we say up front", s_h),
    B("Synthetic rows hold no more information than fob's real data plus what GreenLight borrowed. Ten million rows is a format, not new knowledge."),
    B("Synthetic data cannot reveal a side effect nobody has reported, and cannot replace clinical trials."),
    B("Every synthetic file is labelled with its provenance; nothing is presented as real patients."),
    B("The vote groups outbreaks by who gets sick and who dies, not by virus family (H7N9 influenza looks COVID-like). The lab label "
      "stays a separate input."),
    B("Replays use final, cleaned datasets. Brazil outcomes count from the date they were recorded; Mexico has no outcome date "
      "for survivors, so its replays still use outcomes from admission (optimistic). Mexico is ordered by admission date, which "
      "ignores reporting delay."),
]

doc = SimpleDocTemplate("docs/outbreak-synth-plan.pdf", pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                        topMargin=0.7 * inch, bottomMargin=0.8 * inch, title="GreenLight: plan v3.2",
                        author="outbreak-synth project")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("wrote docs/outbreak-synth-plan.pdf")
