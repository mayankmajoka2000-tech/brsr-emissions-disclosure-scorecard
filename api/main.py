"""
BRSR Emissions Disclosure API.

Serves the FY2025-26 BRSR Scope 1 & 2 disclosure scorecard for 10 Nifty 50 companies:
reported emissions, disclosure scores, the scoring rubric, and a scoring endpoint for
assessing any other company's BRSR against the same rubric.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from scoring import CRITERIA, LEVEL_POINTS, MAX_POINTS, RUBRIC, TOTAL_MAX, company_scores, score_levels

ROOT = Path(__file__).resolve().parents[1]
DATA = pd.read_csv(ROOT / "data" / "brsr_fy26_ghg.csv")
SCORES = company_scores()
VERSION = "1.0.0"

app = FastAPI(
    title="BRSR Emissions Disclosure API",
    version=VERSION,
    description=(
        "Scope 1, 2 and 3 emissions and disclosure-quality scores from the FY2025-26 SEBI Business "
        "Responsibility & Sustainability Reports (BRSR) of 10 Nifty 50 companies. Scores measure how "
        "completely and transparently emissions are disclosed (out of 100), not emissions performance. "
        "Every company record links to its source report."
    ),
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

SOURCE_NOTE = "Company BRSR FY2025-26, Principle 6 Essential Indicator 7 and Leadership Indicator 2"


def _clean(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def _yoy(cur, prev):
    if cur is None or prev in (None, 0):
        return None
    return round(cur / prev - 1, 4)


def _record(row: pd.Series) -> dict:
    r = {k: _clean(v) for k, v in row.to_dict().items()}
    s1, s2 = r["scope1_fy26_tco2e"], r["scope2_fy26_tco2e"]
    return {
        "company": r["company"], "ticker": r["ticker"], "sector": r["sector"],
        "boundary": r["boundary_basis"],
        "emissions_tco2e": {
            "scope1": {"fy26": s1, "fy25": r["scope1_fy25_tco2e"], "yoy": _yoy(s1, r["scope1_fy25_tco2e"])},
            "scope2": {"fy26": s2, "fy25": r["scope2_fy25_tco2e"], "yoy": _yoy(s2, r["scope2_fy25_tco2e"]),
                       "basis_reported": r["scope2_basis_reported"],
                       "location_based_fy26": r["scope2_location_fy26_tco2e"]},
            "scope1_plus_2_fy26": s1 + s2,
            "scope3": {"fy26": r["scope3_fy26_tco2e"], "fy25": r["scope3_fy25_tco2e"],
                       "yoy": _yoy(r["scope3_fy26_tco2e"], r["scope3_fy25_tco2e"])},
        },
        "physical_intensity": {"value": r["physical_intensity_fy26"], "unit": r["physical_intensity_unit"]},
        "assurance": {"provider": r["assurance_provider"], "level": r["assurance_level"]},
        "stated_target": r["stated_target"],
        "notes": r["notes"],
        "source": {"report_url": r["report_url"], "section": SOURCE_NOTE},
    }


RECORDS = {row.ticker.upper(): _record(row) for _, row in DATA.iterrows()}
BY_COMPANY = {rec["company"]: t for t, rec in RECORDS.items()}


def _summary(ticker: str) -> dict:
    rec = RECORDS[ticker]
    s = SCORES[rec["company"]]
    return {"ticker": ticker, "company": rec["company"], "sector": rec["sector"],
            "score": s["total"], "grade": s["grade"], "rank": s["rank"]}


def _get(ticker: str) -> str:
    t = ticker.upper()
    if t not in RECORDS:
        raise HTTPException(404, f"Unknown ticker '{ticker}'. Valid: {sorted(RECORDS)}")
    return t


# ------------------------------------------------------------------------ routes
@app.get("/", tags=["System"])
def root():
    return {
        "name": "BRSR Emissions Disclosure API", "version": VERSION, "status": "operational",
        "docs": "/docs", "reporting_year": "FY2025-26", "companies": len(RECORDS),
        "endpoints": ["/companies", "/companies/{ticker}", "/rankings", "/emissions",
                      "/rubric", "/insights", "/score"],
    }


@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy", "version": VERSION}


@app.get("/companies", tags=["Scorecard"], summary="All companies with score, grade and rank")
def companies(sector: str | None = Query(None, examples=["IT services"]),
              grade: Literal["A", "B", "C", "D"] | None = None):
    rows = [_summary(t) for t in RECORDS]
    if sector:
        rows = [r for r in rows if r["sector"].lower() == sector.lower()]
    if grade:
        rows = [r for r in rows if r["grade"] == grade]
    rows.sort(key=lambda r: (r["rank"], r["company"]))
    return {"count": len(rows), "companies": rows}


@app.get("/companies/{ticker}", tags=["Scorecard"], summary="Full record: emissions, score breakdown, source")
def company(ticker: str):
    t = _get(ticker)
    rec = RECORDS[t]
    s = SCORES[rec["company"]]
    return {**rec, "disclosure_score": {"total": s["total"], "max": TOTAL_MAX, "grade": s["grade"],
                                        "rank": s["rank"], "rationale": s["rationale"],
                                        "breakdown": s["breakdown"]}}


@app.get("/rankings", tags=["Scorecard"], summary="Rank companies overall or on one criterion")
def rankings(criterion: str | None = Query(None, description=f"One of: {', '.join(CRITERIA)}")):
    if criterion is None:
        return companies(sector=None, grade=None)
    if criterion not in MAX_POINTS:
        raise HTTPException(400, f"Unknown criterion. Valid: {CRITERIA}")
    rows = []
    for t, rec in RECORDS.items():
        b = SCORES[rec["company"]]["breakdown"][criterion]
        rows.append({"ticker": t, "company": rec["company"], "level": b["level"],
                     "points": b["points"], "max": b["max"]})
    rows.sort(key=lambda r: (-r["points"], r["company"]))
    return {"criterion": criterion, "count": len(rows), "rankings": rows}


@app.get("/emissions", tags=["Emissions"], summary="Reported Scope 1, 2, 3 emissions (tCO2e)")
def emissions(sort_by: Literal["scope1", "scope2", "scope1_plus_2", "scope3"] = "scope1_plus_2",
              sector: str | None = None):
    rows = []
    for t, rec in RECORDS.items():
        e = rec["emissions_tco2e"]
        if sector and rec["sector"].lower() != sector.lower():
            continue
        rows.append({"ticker": t, "company": rec["company"], "sector": rec["sector"],
                     "scope1": e["scope1"]["fy26"], "scope1_yoy": e["scope1"]["yoy"],
                     "scope2": e["scope2"]["fy26"], "scope2_yoy": e["scope2"]["yoy"],
                     "scope1_plus_2": e["scope1_plus_2_fy26"], "scope3": e["scope3"]["fy26"]})
    rows.sort(key=lambda r: -(r[sort_by] or 0))
    total = sum(r["scope1_plus_2"] for r in rows)
    for r in rows:
        r["share_of_sample_scope1_plus_2"] = round(r["scope1_plus_2"] / total, 4) if total else None
    return {"unit": "tCO2e", "year": "FY2025-26", "count": len(rows),
            "total_scope1_plus_2": total, "companies": rows}


@app.get("/rubric", tags=["Methodology"], summary="The 9 scoring criteria and points per level")
def rubric():
    return {"total_max": TOTAL_MAX,
            "grades": {"A": ">= 85", "B": "70-84", "C": "55-69", "D": "< 55"},
            "criteria": [{"criterion": c, "max_points": mx, "measures": d,
                          "levels": [{"level": l, "points": p} for l, p in lv]}
                         for c, mx, d, lv in RUBRIC]}


@app.get("/insights", tags=["Methodology"], summary="Sample-wide findings computed from the data")
def insights():
    avg = {c: sum(SCORES[r["company"]]["breakdown"][c]["points"] for r in RECORDS.values()) / len(RECORDS)
           for c in CRITERIA}
    pct = {c: round(avg[c] / MAX_POINTS[c], 3) for c in CRITERIA}
    em = emissions()
    top3 = em["companies"][:3]
    gas = [r["company"] for r in RECORDS.values()
           if SCORES[r["company"]]["breakdown"]["Gas-wise breakdown"]["level"] == "Full"]
    dual = [r["company"] for r in RECORDS.values()
            if SCORES[r["company"]]["breakdown"]["Scope 2 method"]["level"] == "Both"]
    return {
        "average_score": round(sum(s["total"] for s in SCORES.values()) / len(SCORES), 1),
        "criterion_average_as_share_of_max": dict(sorted(pct.items(), key=lambda x: x[1])),
        "weakest_criterion": min(pct, key=pct.get),
        "top3_emitters": [r["company"] for r in top3],
        "top3_share_of_scope1_plus_2": round(sum(r["scope1_plus_2"] for r in top3) / em["total_scope1_plus_2"], 3),
        "companies_with_gas_breakdown": gas,
        "companies_with_both_scope2_methods": dual,
        "all_reasonably_assured": all(r["assurance"]["level"] == "Reasonable" for r in RECORDS.values()),
    }


class ScoreRequest(BaseModel):
    company: str = Field("Example Ltd", description="Name of the company being assessed")
    levels: dict[str, str] = Field(
        ..., description="One level per criterion; see GET /rubric for valid levels",
        examples=[dict(zip(CRITERIA, ["Full", "None", "All three", "One stated", "Stated",
                                      "Reasonable", "Standalone", "Total only", "Dated net zero"]))])


@app.post("/score", tags=["Scorecard"], summary="Score any company's BRSR with the same rubric")
def score(req: ScoreRequest):
    try:
        res = score_levels(req.levels)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    beats = sum(1 for s in SCORES.values() if res["total"] > s["total"])
    return {"company": req.company, **res, "max": TOTAL_MAX,
            "would_rank": sum(1 for s in SCORES.values() if s["total"] > res["total"]) + 1,
            "scores_higher_than": f"{beats} of {len(SCORES)} sample companies"}
