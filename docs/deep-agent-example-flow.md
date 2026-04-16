# 🧠 END-TO-END EXAMPLE FLOW

## Final Deep Agent Architecture

---

## 🎯 User Query

> “Find companies with high profitability over the last 3 years, rank them by valuation, and show the trend”
> 

---

# 🔷 STEP 1 — AGENT: QUERY UNDERSTANDING (LLM)

### Input:

Raw query

---

### Output:

```json
{
  "raw_terms": ["high profitability", "valuation", "trend"],
  "intent": ["filter", "rank", "trend"],
  "time": {"type": "last_n_years", "value": 3}
}
```

---

### 🧠 Type: **LLM**

---

# 🔷 STEP 2 — AGENT: AMBIGUITY DETECTION (LLM)

Detected ambiguities:

| Term | Issue |
| --- | --- |
| high profitability | undefined metric |
| valuation | multiple metrics |
| threshold | not specified |

---

### Output:

```json
{
  "ambiguities": [
    {
      "term": "profitability",
      "options": ["ROE", "ROCE", "Net Profit Margin"]
    },
    {
      "term": "valuation",
      "options": ["PE", "PB"]
    },
    {
      "term": "threshold",
      "options": ["user_defined"]
    }
  ]
}
```

---

### 🧠 Type: **LLM**

---

# 🔷 STEP 3 — CLARIFICATION LOOP (LLM + USER)

### Agent asks (MCQ style):

```
What metric should be used for profitability?

A) ROE
B) ROCE
C) Net Profit Margin
D) Custom
```

---

```
What metric should be used for valuation?

A) PE
B) PB
C) Custom
```

---

```
What ROE threshold should be used?

A) >10%
B) >15%
C) >20%
D) Custom
```

---

### User responds:

```
ROE, PE, >15%
```

---

### Updated Query:

```json
{
  "metrics": ["ROE", "PE"],
  "conditions": [
    {"metric": "ROE", "op": ">", "value": 15}
  ],
  "intent": ["filter", "rank", "trend"],
  "time": {"type": "last_n_years", "value": 3}
}
```

---

### 🧠 Type: **LLM + Human**

---

# 🔷 STEP 4 — AGENT: TASK DECOMPOSITION (LLM)

### Plan:

```
Step 1: Filter companies with ROE > 15 over last 3 years
Step 2: Aggregate metrics per company
Step 3: Rank companies by PE (ascending)
Step 4: Select top companies
Step 5: Prepare time-series data for trend visualization
```

---

### 🧠 Type: **LLM**

---

# 🔷 STEP 5 — PRE-EXECUTION VALIDATION (HYBRID)

---

## 5.1 Metric Check (Deterministic)

```
ROE → exists
PE → exists
```

---

## 5.2 Threshold Validation

User-defined:

```
ROE > 15%
```

Dataset stats:

```
ROE range: 2% – 32%
```

Evaluation:

```
Threshold is valid
```

---

## 5.3 Outcome

```
Query is feasible → proceed
```

---

### 🧠 Type: **Hybrid (Data + Logic)**

---

# 🔷 STEP 6 — CODE GENERATION (HYBRID)

LLM generates:

```python
df_filtered = df[df["year"] >= max(df["year"]) - 3]

grouped = df_filtered.groupby("company").agg({
    "ROE": "mean",
    "PE": "mean"
}).reset_index()

filtered = grouped[grouped["ROE"] > 15]

result = filtered.sort_values("PE").head(10)
```

---

### 🧠 Type: **Hybrid**

---

# 🔷 STEP 7 — EXECUTION (DETERMINISTIC)

```
Result: 0 companies
```

---

### 🧠 Type: **Deterministic**

---

# 🔷 STEP 8 — AGENT: RESULT EVALUATION (LLM)

### Input:

- Empty result
- Query context

---

### LLM decides:

```
Threshold too strict → refinement required
```

---

### 🧠 Type: **LLM**

---

# 🔷 STEP 9 — REFINEMENT (LLM + USER)

Agent asks:

```
No companies found with ROE > 15%.

Would you like to:

A) Lower to 12%
B) Lower to 10%
C) View distribution first
D) Keep as is
```

---

### User:

```
A
```

---

### Updated Query:

```json
{
  "conditions": [
    {"metric": "ROE", "op": ">", "value": 12}
  ]
}
```

---

# 🔷 STEP 10 — RE-EXECUTION

```
Result: 5 companies found
```

---

# 🔷 STEP 11 — PLOT DECISION (LLM)

### Input:

- intent = trend
- result size = small
- data type = time series

---

### Decision:

```
Line chart is appropriate
```

---

### 🧠 Type: **LLM**

---

# 🔷 STEP 12 — VALUE NORMALIZATION (DETERMINISTIC)

Since multiple companies are compared:

```python
def normalize(values):
    return (values - min(values)) / (max(values) - min(values))
```

Applied to:

```
ROE trends across companies
```

---

### 🧠 Type: **Deterministic**

---

# 🔷 STEP 13 — PLOT GENERATION (DETERMINISTIC)

```python
generate_line_plot(normalized_data)
```

---

### 🧠 Type: **Deterministic**

---

# 🔷 STEP 14 — INTERPRETATION (LLM)

```
The selected companies demonstrate consistent profitability above 12% over the last 3 years. After normalization, their performance trends show relatively stable growth patterns, indicating sustained operational efficiency. Their lower PE ratios suggest they may still be reasonably valued compared to peers.
```

---

### 🧠 Type: **LLM**

---

# 🔷 STEP 15 — FINAL RESPONSE

```json
{
  "status": "success",
  "summary": "5 companies found",
  "insight": "Consistent profitability with reasonable valuation",

  "confidence": 0.82,

  "clarifications": [
    "profitability → ROE",
    "valuation → PE"
  ],

  "thresholds": {
    "ROE": ">12%"
  },

  "refinements": [
    "ROE threshold adjusted from 15% to 12%"
  ],

  "visualization": {
    "type": "line_chart",
    "normalized": true,
    "reason": "trend comparison across companies"
  },

  "data": [...]
}
```

---

# 🧠 COMPONENT SUMMARY

---

## 🔶 LLM

- Understanding
- Ambiguity detection
- MCQ clarification
- Decomposition
- Evaluation
- Refinement
- Interpretation
- Plot decision

---

## 🔶 Deterministic

- Metric existence check
- Execution
- Value normalization
- Plot rendering

---

## 🔶 Hybrid

- Pre-validation (data-aware)
- Code generation
- Self-correction loop

---

# 🧠 FINAL FLOW SUMMARY

```
Understand → Clarify → Define Thresholds → Plan → Validate → Execute → Evaluate → Refine → Normalize → Explain
```

---

## ✔ Demonstrates:

- No hidden assumptions
- Structured user interaction
- Explicit threshold control
- Efficient execution
- Intelligent refinement
- Interpretable visualization
- Clear reasoning pipeline

---