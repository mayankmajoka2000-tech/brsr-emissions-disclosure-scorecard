# BRSR Scope 1 & 2 Disclosure Scorecard: 10 Nifty 50 Companies (FY2025-26)

How well do India's largest listed companies disclose their greenhouse-gas emissions in their SEBI
**Business Responsibility & Sustainability Reports**? This project scores the FY2025-26 BRSR of
10 Nifty 50 companies across 9 sectors on a 100-point rubric covering completeness, transparency,
methodology and assurance of Scope 1 and 2 disclosure.

It scores **disclosure quality, not emissions performance**: a heavy emitter can score well if it reports clearly.

📊 **Workbook:** [`output/BRSR_Scope1_2_Disclosure_Scorecard_FY26.xlsx`](output/BRSR_Scope1_2_Disclosure_Scorecard_FY26.xlsx)
📁 **Data:** [`data/brsr_fy26_ghg.csv`](data/brsr_fy26_ghg.csv), with a source link for every company

## Results

| Rank | Company | Sector | Score | Grade |
|---|---|---|---|---|
| 1 | Tata Consultancy Services | IT services | 100 | A |
| 2 | HDFC Bank | Banking | 85 | A |
| 3 | Reliance Industries | Oil to chemicals | 84 | B |
| 4 | Infosys | IT services | 80 | B |
| 4 | ITC | FMCG / conglomerate | 80 | B |
| 6 | Mahindra & Mahindra | Automobiles | 79 | B |
| 7 | Tata Steel | Steel | 74 | B |
| 8 | UltraTech Cement | Cement | 64 | C |
| 9 | Larsen & Toubro | Engineering & construction | 60 | C |
| 10 | NTPC | Power generation | 54 | D |

**Average: 76 / 100.**

## Key findings

1. **Assurance is universal, but transparency isn't.** All 10 companies got *reasonable assurance* on their GHG
   figures (a result of SEBI's BRSR Core mandate), so assurance no longer separates leaders from laggards.
   The gaps are in the information around the numbers.

2. **The biggest emitters disclose the least about method.** NTPC, UltraTech and Tata Steel are three of the four
   companies with the highest emissions in the sample, and they account for **92% of the sample's 510 Mt Scope 1+2**.
   They score lowest on methodology and Scope 2 transparency. NTPC alone emits 309 Mt, or 61% of the total,
   yet its BRSR states no calculation standard, no Scope 2 basis and no emission-reduction target.

3. **Gas-wise breakdown is the weakest criterion.** Only 3 of 10 (Reliance, TCS, HDFC Bank) split Scope 1 by gas,
   even though the BRSR format asks for it. The average score here is 30% of the maximum.

4. **Market- versus location-based Scope 2 changes the picture.** Only 4 companies give both figures. Where they do,
   the gap is large: TCS's location-based Scope 2 is **5.9x** its reported figure (318,184 vs 53,971 tCO2e) and
   Infosys's is **4.2x** (145,604 vs 34,351 tCO2e). Renewable-energy procurement claims are hard to judge without both.

5. **Scope 3 figures aren't comparable year to year.** Boundaries changed for NTPC (1.97 Mt to 10.59 Mt after adding
   categories 1-4), Mahindra (+31%, Trucks & Buses added) and ITC (+36%, wider logistics). Reliance's Scope 3 table
   has no values in the filing, and L&T's Scope 3 is explicitly unassured.

6. **Services companies' Scope 1 rose while Scope 2 fell.** Infosys (+31%), HDFC Bank (+18%), Mahindra (+18%) and
   TCS (+10%) reported higher Scope 1 alongside lower Scope 2, which is consistent with renewable electricity
   replacing grid power while fleets, generators and refrigerants grow. HDFC Bank attributes its rise to
   high-GWP fire-suppression agents.

## API

The scorecard is also a FastAPI service (`api/main.py`, interactive docs at `/docs`).

| Endpoint | Returns |
|---|---|
| `GET /companies?sector=&grade=` | All companies with score, grade and rank |
| `GET /companies/{ticker}` | Full record: Scope 1/2/3 with YoY, intensity, assurer, target, score breakdown, source link |
| `GET /rankings?criterion=` | Ranking overall or on one criterion (e.g. `Gas-wise breakdown`) |
| `GET /emissions?sort_by=` | Reported emissions and each company's share of the sample total |
| `GET /rubric` | The 9 criteria and points per level |
| `GET /insights` | Sample-wide findings computed live from the data |
| `POST /score` | Score any other company's BRSR with the same rubric and see where it would rank |

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload        # http://127.0.0.1:8000/docs
pytest -q                            # 10 tests
```

Deploy: `render.yaml` (Render free tier) or `Dockerfile`.

## Scoring rubric (100 points)

| Criterion | Points | Full marks when |
|---|---|---|
| Absolute Scope 1 & 2 | 15 | Both scopes in tCO2e, current and prior year, at usable precision |
| Gas-wise breakdown | 10 | CO2 / CH4 / N2O / HFCs etc. reported |
| Intensity metrics | 15 | Per rupee, PPP-adjusted, and physical output (5 each) |
| Scope 2 method | 10 | Both market- and location-based figures given |
| Methodology & factors | 10 | Standard (GHG Protocol / ISO 14064 / IPCC) and factor sources named |
| External assurance | 15 | Reasonable assurance (limited = 8) |
| Boundary clarity | 5 | Consolidated coverage (standalone = 3) |
| Scope 3 (leadership) | 10 | Category-level breakdown (total only = 6) |
| Reduction target | 10 | SBTi target (dated net-zero only = 6) |

Grades: A >= 85, B 70-84, C 55-69, D < 55. Each company's level on each criterion and the reasoning are on
the workbook's **Assessment** sheet. The scores are live Excel formulas, so changing a level or a weight
recalculates every total and rank.

## Method

- **Sample:** 10 Nifty 50 constituents, weighted toward high emitters (power, cement, steel, oil) with IT,
  banking, FMCG, autos and engineering for contrast.
- **Source:** each company's FY2025-26 BRSR as filed with NSE or published on its website (filed May-Aug 2026).
  Figures were extracted from the PDF text layer (Principle 6, Essential Indicator 7 and Leadership Indicator 2)
  and checked against each report's GHG table.
- **Scope of credit:** only what is in the BRSR itself. Several companies publish more elsewhere (Infosys's ESG
  Databook, Tata Steel's Climate Change Report); that is deliberately not credited, because BRSR is the
  regulated disclosure.
- **Units:** ITC reports in kilotonnes and Tata Steel in million tonnes; all are converted to tCO2e.

## Reproduce

```bash
pip install pandas openpyxl
python build_scorecard.py
```

Figures in `data/brsr_fy26_ghg.csv`; rubric, criterion levels and rationale in `scoring.py`.

## Limitations

Levels are analyst judgements and are documented for each company. Ten companies are a sample, not the whole Nifty 50.
The rubric scores disclosure quality only and says nothing about whether a company's emissions or targets are adequate.

---
*Mayank Majoka, October 2026. Not investment advice.*
