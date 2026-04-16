# NL Financial Query Agent — Progress Report
**Date:** April 16, 2026

---

## 1. Project Summary

A deep-agent system that interprets natural language financial queries, resolves ambiguity through structured MCQ clarification, and returns deterministic results with visualizations. The core design principle: **LLM for reasoning, deterministic layers for correctness**.

Full architecture and design rationale: [`docs/deep-agent-approach.md`](docs/deep-agent-approach.md)  
End-to-end walkthrough: [`docs/deep-agent-example-flow.md`](docs/deep-agent-example-flow.md)

---

## 2. What's Built and Working

### Core Agent Loop — [`agent/agent.py`](agent/agent.py)
- LiteLLM-powered tool-calling loop with support for Groq, Gemini, OpenAI, and Anthropic models
- MCQ clarification intercept: detects when the LLM assumes a numeric threshold from a qualitative word (e.g. "high ROE") and blocks the tool call, asking the user instead
- Refinement loop: when execution returns 0 results, the agent surfaces a threshold-adjustment MCQ
- Structured chain-of-thought logging across 7 stages: `query_understanding`, `ambiguity_detected`, `clarification_received`, `query_execution`, `execution_result`, `threshold_refinement`, `visualization_decision`
- Auto-finalize on successful result: saves JSON, CSV, query code, and plot code to `outputs/`

### System Prompt — [`agent/prompts.py`](agent/prompts.py)
- Clear rules for when to ask vs. when to execute directly
- Explicit prohibition on assuming thresholds for qualitative words
- One-question-at-a-time constraint enforced in prompt
- Post-execution behavior defined: insight on success, refinement MCQ on empty result

### Pre-Execution Validation — [`tools/validate.py`](tools/validate.py)
- Metric existence check against live dataset columns
- Derivability check: currently a hardcoded `DERIVABLE` map — **to be replaced with LLM-driven derivation** (see next steps)
- Per-condition threshold feasibility check with dataset min/max/mean stats
- Returns structured warnings before any compute is spent

### Deterministic Code Generation — [`tools/codegen.py`](tools/codegen.py)
- Generates pandas code from a structured query dict (no LLM involvement)
- Handles: time filtering, per-company aggregation, multi-condition filtering, ranking, trend pivot

### Safe Execution — [`tools/execute_query.py`](tools/execute_query.py)
- Validates query, generates code, runs it in an isolated `exec()` namespace
- Returns result records, trend data, row count, and the generated code itself

### Plot System — [`tools/plot.py`](tools/plot.py)
- `decide_plot`: rule-based decision (trend → line, rank/filter → bar)
- `render_plot`: deterministic matplotlib rendering with normalization applied where appropriate
- Saves PNG to `outputs/`

### Normalization — [`utils/normalize.py`](utils/normalize.py)
- Min-max normalization for comparison/ranking charts
- `should_normalize` logic: skips normalization for percentage metrics (ROE, ROCE, net_profit_margin) and raw time-series trends — **bug: trend case is currently inverted, returns True instead of False (see next steps)**

### Confidence Scoring — [`utils/confidence.py`](utils/confidence.py)
- Penalizes clarifications (−0.1 each), retries (−0.1 each), threshold overrides (−0.05 each)
- Floor at 0.5 — **bug: masks heavily massaged queries; a 5-clarification run scores the same as a 1-clarification run (see next steps)**

### Dataset — [`data/loader.py`](data/loader.py)
- Synthetic: 10 companies × 3 years (2021–2023) × 6 metrics
- Metrics: `ROE`, `ROCE`, `net_profit_margin`, `PE`, `PB`, `revenue`
- Seeded for reproducibility; `get_stats(metric)` exposes min/max/mean/median for validation

---

## 3. Verified End-to-End

Two full runs saved in [`outputs/`](outputs/):

**Run 1** (`result_20260414_122915.json`) — simple filter, direct execution, bar chart  
**Run 2** (`result_20260414_122950.json`) — two-query session demonstrating:
- Ambiguity detection and MCQ clarification ("high ROE" → threshold asked)
- Successful execution (6 companies, ROE > 15)
- Second query with impossible threshold (net_profit_margin > 50) → 0 results → refinement MCQ → re-execution → 9 companies found
- Confidence: 0.80 (2 clarifications, 0 retries, 0 overrides)
- Full chain-of-thought trace with 13 logged steps

Test case coverage documented in [`docs/test.md`](docs/test.md) — 30 queries across 5 tiers from crystal-clear to highly ambiguous.

---

## 4. What's Not Done Yet

Documented in [`docs/next-steps.md`](docs/next-steps.md). Key gaps:

| Gap | Impact |
|---|---|
| `codegen.py` uses a fixed template | Queries like "ROE improved year-over-year" silently produce wrong results |
| Single monolithic tool | Agent can't inspect data before committing to a query |
| `decide_plot` is hardcoded if/else | No scatter plots, no axis reasoning, can't skip trivial plots |
| Validation checks conditions in isolation | `PE < 5 AND ROE > 40` passes validation but almost certainly returns 0 results |
| Derivability uses a hardcoded `DERIVABLE` map | Doesn't scale — any metric not explicitly listed is rejected; LLM should propose derivation formulas dynamically |
| `_has_assumed_threshold` only checks `conditions[0]` and matches any number | Multi-metric qualitative queries skip the guard; second assumed threshold goes through silently |
| `should_normalize` returns `True` for trend intent | Trend charts are normalized, destroying the actual signal — inverted logic, one-line fix |
| Refinement MCQ counted as clarification | Double-penalizes confidence; a threshold adjustment lowers score via both `clarifications` and `refinements` |
| Confidence floor at 0.5 | A heavily massaged query (5 clarifications, 3 retries) scores the same as a clean one-clarification query |

---

## 5. Architecture Snapshot

```
User Query
  → NLQueryAgent.chat()          # agent/agent.py
      → _has_assumed_threshold()  # intercept qualitative words
      → LiteLLM tool-calling loop
          → execute_query_tool()
              → validate_query()  # tools/validate.py
              → generate_code()   # tools/codegen.py
              → exec() sandbox    # tools/execute_query.py
      → refinement MCQ if empty
  → NLQueryAgent.finalize()
      → decide_plot()             # tools/plot.py
      → render_plot()             # tools/plot.py (+ utils/normalize.py)
      → compute_confidence()      # utils/confidence.py
      → save JSON / CSV / code / PNG → outputs/
```

---

## 6. How to Run

```bash
# No API key needed
python test_flow.py

# Live agent (default: Groq llama-3.3-70b-versatile)
python main.py

# Override model
MODEL=gemini/gemini-1.5-flash python main.py
MODEL=openai/gpt-4o python main.py
```

Set your API key in `.env` (see [`.env.example`](.env.example)).
