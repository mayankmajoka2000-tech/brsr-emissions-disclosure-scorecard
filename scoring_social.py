"""
BRSR social performance scoring (FY2025-26).

Scores what the 10 companies *achieve* on the social metrics they disclose in BRSR (Section A
workforce and board tables, Principle 3 well-being and safety, Principle 5 wages and POSH).
Disclosure completeness is not scored: all 10 report these BRSR Core items with reasonable
assurance, so a completeness score would not separate them.

Every metric is scored against a fixed benchmark, not against the other companies, so a score
does not change when the sample changes. Total 100.
"""
from __future__ import annotations

import math

RUBRIC = [
    # key, pillar, max, description, benchmark
    ("women_workforce", "Gender equity", 10, "Women as % of permanent employees", "40% = full marks (linear)"),
    ("women_board", "Gender equity", 10, "Women as % of the Board", "40% = full marks (EU Directive 2022/2381 target)"),
    ("women_kmp", "Gender equity", 5, "At least one woman among Key Managerial Personnel", "yes = 5, no = 0"),
    ("pay_share_ratio", "Gender equity", 10,
     "Women's share of total wages divided by women's share of permanent employees", "1.0 or above = full marks"),
    ("female_retention", "Gender equity", 10,
     "Women still employed 12 months after returning from parental leave", "100% = full marks"),
    ("turnover_gap", "Gender equity", 5, "Female minus male turnover of permanent employees",
     "female at or below male = full; minus 1 point per percentage point above"),
    ("wellbeing_spend", "Well-being", 10, "Spend on employee well-being as % of revenue",
     "1% of revenue = full marks (linear)"),
    ("ltifr", "Safety", 15, "Lost-time injury frequency rate (worst of employees and workers)",
     "0 = full marks, 0.5 or above = 0 (linear)"),
    ("fatalities", "Safety", 25, "Fatalities, employees plus workers (incl. contractors where reported)",
     "0 = full marks, minus 2.5 points per fatality, floor 0"),
]
MAX = {k: m for k, _, m, _, _ in RUBRIC}
TOTAL_MAX = sum(MAX.values())


def _num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == "":
        return None
    return float(v)


def metrics(row: dict) -> dict:
    n = {k: _num(v) for k, v in row.items() if k not in ("ticker", "boundary_note")}
    women_share = n["perm_women"] / n["perm_employees"]
    lt = [x for x in (n["ltifr_employees"], n["ltifr_workers"]) if x is not None]
    fat = sum(x for x in (n["fatalities_employees"], n["fatalities_workers"]) if x is not None)
    return {
        "women_share_employees": round(women_share, 4),
        "women_share_board": round(n["board_women"] / n["board_total"], 4),
        "women_in_kmp": n["kmp_women"] > 0,
        "wages_female_share": n["wages_female_pct"] / 100,
        "pay_share_ratio": round(n["wages_female_pct"] / 100 / women_share, 3),
        "female_retention": n["female_retention_pct"] / 100,
        "male_retention": None if n["male_retention_pct"] is None else n["male_retention_pct"] / 100,
        "turnover_gap_pp": round(n["turnover_female_pct"] - n["turnover_male_pct"], 2),
        "wellbeing_pct_revenue": n["wellbeing_pct_revenue"],
        "ltifr_worst": max(lt) if lt else None,
        "fatalities": int(fat),
        "posh_complaints": int(n["posh_complaints"]),
        "posh_per_1000_women": round(n["posh_complaints"] / n["perm_women"] * 1000, 2),
    }


def score(m: dict) -> dict:
    s = {
        "women_workforce": min(m["women_share_employees"] / 0.40, 1) * 10,
        "women_board": min(m["women_share_board"] / 0.40, 1) * 10,
        "women_kmp": 5 if m["women_in_kmp"] else 0,
        "pay_share_ratio": min(m["pay_share_ratio"], 1) * 10,
        "female_retention": min(m["female_retention"], 1) * 10,
        "turnover_gap": max(5 - max(m["turnover_gap_pp"], 0), 0),
        "wellbeing_spend": min(m["wellbeing_pct_revenue"] / 1.0, 1) * 10,
        "ltifr": (1 - min(m["ltifr_worst"] / 0.5, 1)) * 15 if m["ltifr_worst"] is not None else 0,
        "fatalities": max(25 - 2.5 * m["fatalities"], 0),
    }
    s = {k: round(v, 1) for k, v in s.items()}
    total = round(sum(s.values()), 1)
    pillars = {}
    for k, p, mx, _, _ in RUBRIC:
        pillars.setdefault(p, {"score": 0.0, "max": 0})
        pillars[p]["score"] = round(pillars[p]["score"] + s[k], 1)
        pillars[p]["max"] += mx
    return {"total": total, "pillars": pillars, "breakdown": s}
