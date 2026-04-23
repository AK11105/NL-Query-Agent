# Query Test Cases

All queries typed at the `You` prompt in `python main.py`.  
Dataset: 1369 companies, fiscal years 2015–2025, metrics: ROE, ROCE, ROA, net_profit_margin, EPS, earnings_yield, enterprise_value, PB, price_to_revenue, revenue_per_share.

Metric ranges (for reference):
- ROE: -99.7 to 40, mean 8.6
- ROCE: -49.4 to 50, mean 12.4
- ROA: -20 to 30, mean 5.3
- net_profit_margin: -30 to 50, mean 8.7
- EPS: -489 to 4812, mean 24.4
- earnings_yield: -0.15 to 0.25, mean 0.04
- enterprise_value: -446 to 950998 Cr, mean 16124
- PB: 0.1 to 20, mean 3.7
- price_to_revenue: 0.1 to 15, mean 3.0
- revenue_per_share: 0 to 46904, mean 358

---

## Tier 1 — Crystal Clear (zero ambiguity, agent should call tool immediately)

**1.1 — Single metric filter, explicit threshold**
```
Show companies with ROE > 20 over the last 3 years
```
Expected: no clarification, direct execution, bar chart.

**1.2 — Two metrics, explicit conditions, explicit rank**
```
Filter companies where ROCE > 15 and PB < 3, rank by ROCE ascending, last 3 years
```
Expected: no clarification, two conditions, bar chart ranked by ROCE.

**1.3 — Explicit trend request**
```
Show the ROE trend for all companies from 2021 to 2023
```
Expected: no clarification, line chart, all companies in result.

**1.4 — EPS filter with explicit threshold**
```
Which companies had EPS above 100 in the last 3 years?
```
Expected: no clarification, filters on EPS > 100, bar chart.

**1.5 — Rank only, no filter**
```
Rank all companies by net_profit_margin descending for the last 3 years
```
Expected: no clarification, no conditions, sort by net_profit_margin desc.

**1.6 — Bottom performers**
```
Show the 5 companies with the lowest PB ratio over the last 3 years
```
Expected: no clarification, rank_ascending=True on PB, head(5).

**1.7 — Two conditions, explicit rank, explicit time**
```
Companies with ROCE > 20 and net_profit_margin > 15, ranked by ROCE descending, last 2 years
```
Expected: two conditions, rank by ROCE desc, time=last_2_years.

---

## Tier 2 — Mostly Clear (one ambiguous term or missing threshold)

**2.1 — Metric clear, threshold missing**
```
Show companies with high ROE over the last 3 years
```
Expected: one clarification — what threshold for ROE? (e.g. A/>10 B/>15 C/>20 D/Custom)

**2.2 — Intent clear, metric ambiguous**
```
Which companies are the most profitable over the last 3 years?
```
Expected: one clarification — which metric? (ROE / ROCE / net_profit_margin / ROA)

**2.3 — Filter clear, rank metric ambiguous**
```
Find companies with ROE > 15 and rank them by valuation
```
Expected: one clarification — which valuation metric? (PB / price_to_revenue / earnings_yield)

**2.4 — Trend request, metric ambiguous**
```
Show me the profitability trend for top companies
```
Expected: clarification — which metric for profitability?

**2.5 — Superlative with no metric**
```
Which companies have the best fundamentals?
```
Expected: clarification — what defines "best fundamentals"? (ROE / ROCE / net_profit_margin)

---

## Tier 3 — Moderately Ambiguous (multiple undefined terms)

**3.1 — Two vague terms**
```
Find good companies with strong earnings
```
Expected: clarifications — metric + threshold for "good", metric + threshold for "strong earnings".

**3.2 — Vague comparative**
```
Which companies are undervalued?
```
Expected: clarifications — which metric? (PB / price_to_revenue / earnings_yield), what threshold?

**3.3 — Relative language**
```
Show me companies that are doing better than average
```
Expected: clarification — which metric? (dataset mean for ROE is ~8.6, ROCE ~12.4 — agent should surface these)

**3.4 — Composite intent**
```
Find profitable companies that are also cheap to buy
```
Expected: clarifications — profitability metric + threshold; valuation metric + threshold.

**3.5 — Trend + filter both vague**
```
Show the growth trend for the best performing companies
```
Expected: clarifications — metric for growth, metric + threshold for "best performing".

---

## Tier 4 — Highly Ambiguous (almost everything undefined)

**4.1 — Pure vague intent**
```
Show me good stocks
```
Expected: full clarification round — metric, threshold, time range.

**4.2 — Narrative style**
```
I want to invest in a solid company that makes good money and isn't too expensive
```
Expected: MCQ — profitability metric + threshold, valuation metric + threshold.

**4.3 — Single word**
```
Profitable?
```
Expected: clarifications — which metric, threshold, time range, intent.

**4.4 — Contradictory / likely-empty**
```
Find companies with very high ROE and very low PB and very high EPS
```
Expected: clarifications on all three thresholds; likely triggers refinement MCQ after execution (ROE > 30 AND PB < 1 AND EPS > 500 will return very few or 0 results).

---

## Tier 5 — Edge Cases & Stress Tests

**5.1 — Threshold that guarantees 0 results**
```
Companies with ROE > 50
```
Expected: pre-validation warns threshold exceeds dataset max (39.99); if executed, 0 results → refinement MCQ.

**5.2 — Invalid metric name**
```
Show companies with PE > 10
```
Expected: validation error — PE not in dataset; agent lists available metrics (earnings_yield is the inverse).

**5.3 — Follow-up query after results**
```
[after any successful result]
Now filter those to only PB < 2
```
Expected: agent re-executes with added condition on top of previous context.

**5.4 — Refinement acceptance**
```
[after 0-result query]
Lower the threshold
```
Expected: agent asks which level (MCQ), override counter increments, confidence penalised.

**5.5 — Trend with single year**
```
Show ROE trend over the last 1 year
```
Expected: executes, line chart has one point per company — agent may note this.

**5.6 — All companies, no filter**
```
Show me all companies and all their metrics
```
Expected: no conditions, all metrics, no clarification.

**5.7 — Metric spelled loosely**
```
Show companies with net profit margin > 10
```
Expected: agent maps "net profit margin" → net_profit_margin and executes directly.

**5.8 — Large EPS filter**
```
Companies with EPS above 500 last 3 years
```
Expected: executes (EPS max is 4812, so feasible), small result set, bar chart.

**5.9 — earnings_yield as proxy for cheap valuation**
```
Show companies with earnings_yield > 0.08 ranked by earnings_yield descending
```
Expected: no clarification, direct execution (0.08 is above mean 0.04, below max 0.25).
