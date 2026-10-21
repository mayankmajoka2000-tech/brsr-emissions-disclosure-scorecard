from fastapi.testclient import TestClient

from api.main import app
from scoring import CRITERIA

client = TestClient(app)


def test_root_and_health():
    assert client.get("/").json()["companies"] == 10
    assert client.get("/health").json()["status"] == "healthy"


def test_companies_ranked():
    body = client.get("/companies").json()
    assert body["count"] == 10
    first, last = body["companies"][0], body["companies"][-1]
    assert (first["ticker"], first["score"], first["grade"]) == ("TCS", 100, "A")
    assert (last["ticker"], last["score"], last["grade"]) == ("NTPC", 54, "D")


def test_filters():
    assert client.get("/companies", params={"grade": "C"}).json()["count"] == 2
    assert client.get("/companies", params={"sector": "it services"}).json()["count"] == 2


def test_company_detail():
    b = client.get("/companies/reliance").json()
    assert b["emissions_tco2e"]["scope1"]["fy26"] == 36350070
    assert b["emissions_tco2e"]["scope2"]["location_based_fy26"] == 2532081
    assert b["disclosure_score"]["total"] == 84
    assert sum(v["points"] for v in b["disclosure_score"]["breakdown"].values()) == 84
    assert b["source"]["report_url"].startswith("https://")
    assert client.get("/companies/XYZ").status_code == 404


def test_rankings_overall():
    r = client.get("/rankings")
    assert r.status_code == 200
    assert r.json()["companies"][0]["ticker"] == "TCS" and r.json()["count"] == 10


def test_every_get_endpoint_without_params():
    for path in ["/", "/health", "/companies", "/rankings", "/emissions", "/rubric", "/insights",
                 "/companies/TCS"]:
        assert client.get(path).status_code == 200, path


def test_rankings_by_criterion():
    b = client.get("/rankings", params={"criterion": "Gas-wise breakdown"}).json()
    assert [r["points"] for r in b["rankings"]][:3] == [10, 10, 10]
    assert client.get("/rankings", params={"criterion": "nope"}).status_code == 400


def test_emissions_concentration():
    b = client.get("/emissions").json()
    assert b["companies"][0]["ticker"] == "NTPC"
    assert abs(b["companies"][0]["share_of_sample_scope1_plus_2"] - 0.606) < 0.001


def test_insights():
    b = client.get("/insights").json()
    assert b["average_score"] == 76.0
    assert b["weakest_criterion"] == "Gas-wise breakdown"
    assert b["all_reasonably_assured"] is True
    assert abs(b["top3_share_of_scope1_plus_2"] - 0.919) < 0.001


def test_rubric_sums_to_100():
    assert client.get("/rubric").json()["total_max"] == 100


def test_score_custom_company():
    levels = dict(zip(CRITERIA, ["Full", "Full", "All three", "Both", "Stated",
                                 "Reasonable", "Consolidated", "Category breakdown", "SBTi"]))
    b = client.post("/score", json={"company": "X", "levels": levels}).json()
    assert b["total"] == 100 and b["grade"] == "A" and b["would_rank"] == 1


def test_score_rejects_bad_level():
    levels = dict(zip(CRITERIA, ["Full"] * len(CRITERIA)))
    assert client.post("/score", json={"levels": levels}).status_code == 422
    assert client.post("/score", json={"levels": {"Gas-wise breakdown": "Full"}}).status_code == 422


def test_social_endpoints():
    for path in ["/social/companies", "/social/companies/TCS", "/social/rubric", "/social/insights"]:
        assert client.get(path).status_code == 200, path
    b = client.get("/social/companies").json()
    assert b["count"] == 10 and b["companies"][0]["ticker"] == "TCS"
    assert client.get("/social/rubric").json()["total_max"] == 100


def test_social_metrics_match_reports():
    r = client.get("/social/companies/RELIANCE").json()
    assert r["metrics"]["women_share_employees"] == round(2377 / 34066, 4)
    assert r["metrics"]["fatalities"] == 3
    lt = client.get("/social/companies/LT").json()
    assert lt["metrics"]["fatalities"] == 30 and lt["breakdown"]["fatalities"] == 0
    assert abs(sum(lt["breakdown"].values()) - lt["score"]) < 0.11


def test_social_insights():
    b = client.get("/social/insights").json()
    assert b["companies_meeting_40pct_women_on_board"] == []
    assert b["total_fatalities"] == 46  # 30 + 5 + 4 + 3 + 3 + 1
