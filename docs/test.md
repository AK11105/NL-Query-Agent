# Query Test Cases

All queries typed at the `You` prompt in `python main.py`.  
Dataset: 10 companies × 3 years (2021–2023), metrics: ROE, ROCE, net_profit_margin, PE, PB, revenue.

---

## Tier 1 — Crystal Clear (zero ambiguity, agent should call tool immediately)

**1.1 — Single metric filter, explicit threshold, explicit time**
```
Show me companies with ROE > 20% over the last 3 years
```
Expected: no clarification, direct execution, bar/line chart.

**1.2 — Two metrics, explicit conditions, explicit rank**
```
Filter companies where ROE > 15 and PE < 20, rank by PE ascending, last 3 years
```
Expected: no clarification, executes with both conditions, bar chart ranked by PE.

**1.3 — Explicit trend request**
```
Show the ROE trend for all companies from 2021 to 2023
```
Expected: no clarification, line chart, all 10 companies.

**1.4 — Revenue filter with explicit threshold**
```
Which companies had revenue above 3000 in the last 3 years?
```
Expected: no clarification, filters on revenue > 3000, bar chart.

**1.5 — Rank only, no filter**
```
Rank all companies by net_profit_margin descending for the last 3 years
```
Expected: no clarification, no conditions, sort by net_profit_margin desc.

**1.6 — Bottom performers**
```
Show the 3 companies with the lowest PB ratio over the last 3 years
```
Expected: no clarification, rank_ascending=True on PB, head(3).

**1.7 — Exact metric name, exact threshold, exact year count**
```
Companies with ROCE > 18 and net_profit_margin > 10, ranked by ROCE descending, last 2 years
```
Expected: two conditions, rank by ROCE desc, time=last_2_years.

---

## Tier 2 — Mostly Clear (one ambiguous term or missing threshold)

**2.1 — Metric clear, threshold missing**
```
Show companies with high ROE over the last 3 years
```
Expected: one clarification — what threshold for ROE? (A/>10 B/>15 C/>20 D/Custom)

**2.2 — Intent clear, metric ambiguous**
```
Which companies are the most profitable over the last 3 years?
```
Expected: one clarification — which metric defines profitability? (ROE / ROCE / net_profit_margin)

**2.3 — Filter clear, rank metric ambiguous**
```
Find companies with ROE > 15 and rank them by valuation
```
Expected: one clarification — which metric for valuation? (PE / PB)

**2.4 — Time range missing**
```
Show companies with PE < 15 ranked by ROE descending
```
Expected: one clarification — over how many years? (1 / 2 / 3)

**2.5 — Trend request, metric ambiguous**
```
Show me the profitability trend for top companies
```
Expected: clarifications — which metric for profitability? what threshold for "top"?

**2.6 — Superlative with no metric**
```
Which companies have the best fundamentals?
```
Expected: clarifications — what defines "best fundamentals"? (ROE / ROCE / net_profit_margin / composite)

---

## Tier 3 — Moderately Ambiguous (multiple undefined terms)

**3.1 — Two vague terms**
```
Find good companies with strong earnings
```
Expected: clarifications — what defines "good"? what defines "strong earnings"? threshold for each?

**3.2 — Vague comparative**
```
Which companies are undervalued?
```
Expected: clarifications — which valuation metric? (PE / PB), what threshold defines undervalued?

**3.3 — Relative language**
```
Show me companies that are doing better than average
```
Expected: clarifications — better than average on which metric? use dataset mean as threshold or custom?

**3.4 — Composite intent**
```
Find profitable companies that are also cheap to buy
```
Expected: clarifications — metric for profitability, threshold; metric for "cheap" (PE/PB), threshold.

**3.5 — Trend + filter both vague**
```
Show the growth trend for the best performing companies
```
Expected: clarifications — metric for growth (revenue / ROE), metric for "best performing", threshold.

**3.6 — Implicit time**
```
Which companies have consistently high margins?
```
Expected: clarifications — which margin metric? what threshold? "consistently" = all 3 years or average?

---

## Tier 4 — Highly Ambiguous (almost everything undefined)

**4.1 — Pure vague intent**
```
Show me good stocks
```
Expected: full clarification round — metric, threshold, time range, rank preference.

**4.2 — Buzzword query**
```
Find quality companies with a margin of safety
```
Expected: clarifications — "quality" metric + threshold, "margin of safety" metric (PB/PE) + threshold.

**4.3 — Narrative style**
```
I want to invest in a solid company that makes good money and isn't too expensive
```
Expected: full MCQ — profitability metric + threshold, valuation metric + threshold, time range.

**4.4 — Single word**
```
Profitable?
```
Expected: clarifications — which metric, threshold, time range, intent (filter/rank/trend).

**4.5 — Contradictory / impossible sounding**
```
Find companies with very high ROE and very low PE and very high revenue
```
Expected: clarifications on all three thresholds; after execution likely triggers refinement MCQ if 0 results.

**4.6 — No financial context at all**
```
Who should I invest in?
```
Expected: agent asks for clarification on what criteria matter (profitability / valuation / growth).

---

## Tier 5 — Edge Cases & Stress Tests

**5.1 — Threshold that guarantees 0 results (refinement loop test)**
```
Companies with ROE > 99%
```
Expected: pre-validation warns threshold exceeds dataset max; if executed, 0 results trigger refinement MCQ.

**5.2 — Invalid metric name**
```
Show companies with EPS > 5
```
Expected: validation error — EPS not in dataset; agent lists available metrics.

**5.3 — Follow-up query after results (multi-turn test)**
```
[after any successful result]
Now filter those to only PE < 15
```
Expected: agent re-executes with added condition on top of previous context.

**5.4 — Refinement acceptance (override tracking test)**
```
[after 0-result query]
Lower the threshold
```
Expected: agent asks which level to lower to (MCQ), override counter increments, confidence penalised.

**5.5 — Trend with single year (degenerate case)**
```
Show ROE trend over the last 1 year
```
Expected: executes, but line chart has only one point per company — agent may note this.

**5.6 — All companies, no filter**
```
Show me all companies and all their metrics
```
Expected: no conditions, all metrics, bar chart or table, no clarification needed.

**5.7 — Rank with no data surviving filter**
```
Companies with net_profit_margin > 50 ranked by revenue
```
Expected: 0 results, refinement MCQ triggered.

**5.8 — Metric spelled wrong**
```
Show companies with net profit margin > 10
```
Expected: agent maps "net profit margin" -> net_profit_margin (or asks for clarification if it can't resolve).
