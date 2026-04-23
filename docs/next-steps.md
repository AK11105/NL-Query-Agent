# Next Steps — Agentic Improvements

These improvements make the agent reason *through* tools rather than just *before* them, while fully preserving the no-assumptions, transparent-by-design constraint.

---

## 1. Replace Template Codegen with LLM-Written Pandas Code

**Current:** `tools/codegen.py` string-interpolates a structured query dict into a fixed pandas template. The LLM never touches the code.

**Problem:** Queries that don't fit the template (e.g. "companies where ROE improved year-over-year", "top 3 by revenue growth rate") silently produce wrong or incomplete results.

**Fix:** Remove `codegen.py`. Give the LLM the dataframe schema and let it write the pandas code directly. Keep `execute_query.py`'s `exec()` sandbox for safe execution.

**Transparency preserved:** Generated code is already saved to `outputs/query_*.py` — that continues unchanged.

---

## 2. Break the Single Tool into Granular Tools

**Current:** One tool — `execute_query_tool` — takes a fully-formed structured query and does everything in one shot. The agent has no ability to explore before committing.

**Problem:** The agent can't inspect data before deciding how to query it, can't adjust mid-reasoning, can't separate "what does the data look like" from "run the actual query".

**Fix:** Replace with smaller composable tools:
- `get_schema()` — returns columns, types, sample values
- `get_stats(metric)` — returns min/max/mean/std for a metric (already exists in `data/loader.py`, just not exposed as a tool)
- `run_code(code)` — executes pandas code, returns result + row count
- `render_plot(result, plot_type, x, y, title)` — renders and saves plot

The agent then plans: inspect schema → write code → run → if empty, ask user via MCQ → plot.

**Transparency preserved:** Chain-of-thought logging in `_log()` captures each step; all tool calls are already appended to `self.history`.

---

## 3. LLM-Driven Plot Decisions

**Current:** `tools/plot.py::decide_plot` is a hardcoded if/else on intent strings:
```python
if "trend" in intent: → line
if "rank" in intent:  → bar
else:                 → bar
```

**Problem:** The LLM can't choose a scatter plot, can't reason about axis assignment, can't decide to skip a plot when the result is trivial (e.g. 1 company).

**Fix:** Pass result shape and metrics to the LLM and let it decide plot type + axes with a brief reasoning note. `render_plot` stays deterministic — only the *decision* moves to the LLM.

**Transparency preserved:** Plot decision reasoning gets logged to `chain_of_thought` under `visualization_decision` stage, same as today.

---

## 4. Agent-Driven Validation via `get_stats`

**Current:** `tools/validate.py` checks each condition in isolation — metric exists, threshold in range. It can't reason about combinations.

**Problem:** A query like `ROCE < 5 AND ROE > 35` passes validation (each condition is individually feasible) but will almost certainly return 0 results. The agent only discovers this after execution, triggering the refinement loop unnecessarily.

**Fix:** Expose `get_stats` as a tool. Before committing to a query with multiple conditions, the agent calls `get_stats` on each metric, reasons about joint feasibility, and surfaces a clarification MCQ *before* execution if the combination looks infeasible.

**Transparency preserved:** The agent explains *why* a threshold combination is risky before asking the user to adjust, rather than just returning empty results.

---

## 5. LLM-Driven Derivability Check

**Current:** `tools/validate.py` has a hardcoded `DERIVABLE` dict with one entry. Any metric not explicitly listed is rejected as unknown, even if trivially computable from available columns.

**Fix:** Remove the `DERIVABLE` map. When a requested metric isn't in the dataset, pass the metric name and available columns to the LLM and ask it to propose a derivation formula. Confirm with the user before executing.

**Transparency preserved:** Proposed formula shown to user for confirmation before any execution.

---

## 10. Agentic Framework — LangGraph (after steps 2–4)

**Current system: no framework needed.**  
The current loop (1 tool, 2 interrupt points) is simple enough that the `while True` loop handles it cleanly.

**After steps 2–4:** The agent will have 4–5 tools and 3–4 hard interrupt points (clarification, feasibility warning, empty result, plot confirmation). At that point the `while True` loop becomes a tangle of flags. LangGraph replaces it with an explicit graph where each stage is a node and each decision is an edge.

| Phase | Framework |
|---|---|
| Current system (1 tool, 2 interrupts) | None — loop is sufficient |
| After steps 2–4 (4+ tools, 3+ interrupts) | LangGraph — loop becomes unmaintainable |

---

## 11. Save `insight` and `thresholds` to Output JSON

**Design doc specifies** (Section 10) that the final response includes:
```json
{
  "insight": "Consistent profitability with reasonable valuation...",
  "thresholds": {"ROE": ">15%"}
}
```

**Current:** `finalize()` saves `clarifications` and `refinements` but never the LLM's insight text or the resolved thresholds. The insight is only printed to console and lost.

**Fix:** In `finalize()`, extract the last non-MCQ assistant message as `insight`, and reconstruct `thresholds` from `last_query["conditions"]` as `{metric: "op value"}` pairs. Add both to the saved JSON.

---

## 12. "View Distribution First" Option in Refinement MCQ

**Design doc specifies** (Step 9) the refinement MCQ should offer:
```
A) Lower to 12%
B) Lower to 10%
C) View distribution first
D) Keep as is
```

**Current:** Only "Lower to X" and "Keep as is" are offered. The user has no way to inspect dataset stats before deciding.

**Fix:** Add a "View distribution first" option to the refinement MCQ. When selected, call `get_stats(metric)` and display min/max/mean/median before re-asking the refinement question.

---

## 13. Multi-Turn Session Context (Follow-up Queries)

**Design doc implies** the agent maintains context across queries in a session (test case 5.3: "Now filter those to only PB < 2").

**Current:** `last_result` is reset to `None` after `finalize()`, and `last_query` is also stale. A follow-up query has no way to reference the previous result set — the agent re-queries from scratch.

**Fix:** Preserve `last_query` across turns. When the agent detects a follow-up (additive language: "now filter", "also", "from those"), merge the new condition into `last_query` rather than starting fresh. The conversation history already carries context — the LLM just needs to be allowed to use it.

---

## 14. Task Decomposition Logged to Chain-of-Thought

**Design doc specifies** (Step 4) the agent should explicitly plan before executing:
```
Step 1: Filter companies by profitability
Step 2: Aggregate metrics per company
Step 3: Rank by valuation
Step 4: Prepare trend data
```

**Current:** The agent jumps straight from clarification to tool call with no visible plan step. The CoT log has no `task_decomposition` stage.

**Fix:** Add a `task_decomposition` stage to `_log()`. After clarifications are resolved and before the tool call, the LLM's reasoning about how to decompose the query should be captured. This is a prompt + logging change, not a new tool.
