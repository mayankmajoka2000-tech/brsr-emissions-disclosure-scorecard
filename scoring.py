"""
Scoring model shared by the Excel builder and the API.

RUBRIC     : 9 criteria, max points and the points for each level (sums to 100).
ASSESSMENT : the level assigned to each company on each criterion, with a one-line rationale.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- rubric
# (criterion, max, description, [(level, points), ...])
RUBRIC = [
    ("Absolute Scope 1 & 2", 15,
     "Scope 1 and Scope 2 reported in tCO2e for current and prior year at usable precision",
     [("Full", 15), ("Rounded", 12), ("Partial", 7), ("Missing", 0)]),
    ("Gas-wise breakdown", 10,
     "Break-up into CO2, CH4, N2O, HFCs etc., as the BRSR format requests 'if available'",
     [("Full", 10), ("Partial", 5), ("None", 0)]),
    ("Intensity metrics", 15,
     "Per rupee of turnover, PPP-adjusted, and physical-output intensity (5 points each)",
     [("All three", 15), ("Two", 10), ("One", 5), ("None", 0)]),
    ("Scope 2 method", 10,
     "States market- vs location-based; full marks when both figures are given",
     [("Both", 10), ("One stated", 5), ("Not stated", 0)]),
    ("Methodology & factors", 10,
     "Names the standard (GHG Protocol / ISO 14064 / IPCC) and emission-factor sources",
     [("Stated", 10), ("Referenced elsewhere", 5), ("Not stated", 0)]),
    ("External assurance", 15,
     "Independent assurance of the GHG figures and its level",
     [("Reasonable", 15), ("Limited", 8), ("None", 0)]),
    ("Boundary clarity", 5,
     "Clear organisational boundary; consolidated coverage scores higher",
     [("Consolidated", 5), ("Standalone", 3), ("Unclear", 0)]),
    ("Scope 3 (leadership)", 10,
     "Voluntary Scope 3 disclosure; category-level split scores higher",
     [("Category breakdown", 10), ("Total only", 6), ("Not disclosed", 0)]),
    ("Reduction target", 10,
     "Science-based target, or at least a dated net-zero / neutrality commitment",
     [("SBTi", 10), ("Dated net zero", 6), ("None found", 0)]),
]
CRITERIA = [r[0] for r in RUBRIC]

# --------------------------------------------------------------------------- assessment
# level per criterion (order = CRITERIA), plus one-line rationale
ASSESSMENT = {
    "Reliance Industries": (["Full", "Full", "All three", "Both", "Stated", "Reasonable", "Standalone", "Not disclosed", "Dated net zero"],
        "Best-in-class gas split and dual Scope 2; Scope 3 table left without values."),
    "Tata Consultancy Services": (["Full", "Full", "All three", "Both", "Stated", "Reasonable", "Consolidated", "Category breakdown", "SBTi"],
        "Complete on every criterion: gas split, factor sources, 7-category Scope 3, 1.5C SBTi target."),
    "Infosys": (["Full", "None", "All three", "Both", "Stated", "Reasonable", "Standalone", "Total only", "Dated net zero"],
        "Strong, but gas split and Scope 3 categories pushed to the ESG Databook rather than the BRSR."),
    "HDFC Bank": (["Full", "Full", "All three", "One stated", "Stated", "Reasonable", "Standalone", "Total only", "Dated net zero"],
        "Detailed gas split and factors; no location-based Scope 2; financed emissions absent."),
    "ITC": (["Full", "None", "All three", "Both", "Stated", "Reasonable", "Standalone", "Total only", "Dated net zero"],
        "ISO 14064 inventory with dual Scope 2; no gas split; kilotonne precision."),
    "NTPC": (["Full", "None", "All three", "Not stated", "Not stated", "Reasonable", "Standalone", "Total only", "None found"],
        "India's largest emitter: figures assured but no method, Scope 2 basis or reduction target."),
    "UltraTech Cement": (["Full", "None", "All three", "Not stated", "Not stated", "Reasonable", "Standalone", "Total only", "SBTi"],
        "SBTi-validated targets, but BRSR omits methodology and Scope 2 basis."),
    "Larsen & Toubro": (["Full", "None", "Two", "Not stated", "Referenced elsewhere", "Reasonable", "Standalone", "Total only", "Dated net zero"],
        "No physical intensity, gas split or Scope 2 basis; Scope 3 explicitly unassured."),
    "Mahindra & Mahindra": (["Full", "None", "All three", "One stated", "Stated", "Reasonable", "Standalone", "Total only", "SBTi"],
        "GHG Protocol + ISO 14064-3 verified, segment intensities; no gas split."),
    "Tata Steel": (["Rounded", "None", "All three", "One stated", "Stated", "Reasonable", "Consolidated", "Total only", "Dated net zero"],
        "Only company giving standalone and consolidated; figures rounded to whole Mt."),
}


LEVEL_POINTS = {crit: dict(levels) for crit, _, _, levels in RUBRIC}
MAX_POINTS = {crit: mx for crit, mx, _, _ in RUBRIC}
TOTAL_MAX = sum(MAX_POINTS.values())


def grade(total: float) -> str:
    return "A" if total >= 85 else "B" if total >= 70 else "C" if total >= 55 else "D"


def score_levels(levels: dict[str, str]) -> dict:
    """Score a {criterion: level} mapping. Raises ValueError on unknown criteria or levels."""
    missing = [c for c in CRITERIA if c not in levels]
    unknown = [c for c in levels if c not in LEVEL_POINTS]
    if missing or unknown:
        raise ValueError(f"missing criteria: {missing}; unknown criteria: {unknown}")
    breakdown = {}
    for crit in CRITERIA:
        lvl = levels[crit]
        if lvl not in LEVEL_POINTS[crit]:
            raise ValueError(f"'{lvl}' is not a level of '{crit}'. Valid: {list(LEVEL_POINTS[crit])}")
        breakdown[crit] = {"level": lvl, "points": LEVEL_POINTS[crit][lvl], "max": MAX_POINTS[crit]}
    total = sum(v["points"] for v in breakdown.values())
    return {"total": total, "grade": grade(total), "breakdown": breakdown}


def company_scores() -> dict[str, dict]:
    """Scores for every assessed company, with rank (ties share a rank)."""
    out = {}
    for comp, (levels, why) in ASSESSMENT.items():
        res = score_levels(dict(zip(CRITERIA, levels)))
        res["rationale"] = why
        out[comp] = res
    totals = sorted((v["total"] for v in out.values()), reverse=True)
    for v in out.values():
        v["rank"] = totals.index(v["total"]) + 1
    return out
