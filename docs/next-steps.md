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

**Problem:** A query like `PE < 5 AND ROE > 40` passes validation (each condition is individually feasible) but will almost certainly return 0 results. The agent only discovers this after execution, triggering the refinement loop unnecessarily.

**Fix:** Expose `get_stats` as a tool. Before committing to a query with multiple conditions, the agent calls `get_stats` on each metric, reasons about joint feasibility, and surfaces a clarification MCQ *before* execution if the combination looks infeasible.

**Transparency preserved:** This is strictly more transparent — the agent explains *why* a threshold combination is risky before asking the user to adjust, rather than just returning empty results.

---

## 5. LLM-Driven Derivability Check

**Current:** `tools/validate.py` has a hardcoded `DERIVABLE` dict mapping metric names to required columns and a formula description:
```python
DERIVABLE = {
    "gross_margin": ({"revenue"}, "revenue-based approximation"),
}
```

**Problem:** This doesn't scale — there are hundreds of financial metrics that could be derived from the available columns. Maintaining a static map means any metric not explicitly listed is rejected as unknown, even if it's trivially computable from the data.

**Fix:** Remove the `DERIVABLE` map. When a requested metric isn't found in the dataset, pass the metric name and the available columns to the LLM and ask it to propose a derivation formula. If the LLM can produce one, confirm with the user before executing. The `exec()` sandbox already handles arbitrary pandas code, so the derived column just gets added before the filter step.

**Transparency preserved:** The proposed formula is shown to the user for confirmation before any execution — same no-assumptions guarantee as the rest of the system.

---

## 6. Harden `_has_assumed_threshold` — Only Check First Condition

**Current:** `agent/agent.py::_has_assumed_threshold` uses a regex heuristic to detect when the LLM assumed a numeric threshold from a qualitative word (e.g. "cheap", "high"). It also only inspects `conditions[0]`.

**Problems:**
- If the user's query contains a qualitative word *and* an unrelated number (e.g. "top 5 high-ROE companies"), `_HAS_NUMBER` matches and the guard is skipped — the assumption goes undetected.
- If the LLM assumed thresholds on two metrics simultaneously (e.g. "good companies with cheap valuation"), only the first condition is intercepted; the second assumption goes through silently.

**Fix:** Tighten `_HAS_NUMBER` to only match if the number is associated with a condition on the *same metric* as the qualitative word. Also loop over all conditions, not just `conditions[0]`.

**Transparency preserved:** Bug fix for the existing transparency mechanism — no behavioral change when working correctly.

---

## 7. Fix `should_normalize` — Trend Must Never Normalize

**Current:** `utils/normalize.py::should_normalize` returns `True` when `"trend"` is in intent:
```python
if "trend" in intent:
    return True   # normalize trend lines for comparison
```

**Problem:** This is inverted. Normalizing a trend chart collapses all companies to the same 0–1 range and destroys the actual signal — a company going from ROE 8→12 looks identical to one going from 20→24. Trend charts must show raw values so the viewer can see real movement and magnitude.

**Fix:** One-line correction:
```python
if "trend" in intent:
    return False
```
Normalization should only apply to cross-entity comparisons (bar charts) where metrics are on different scales (e.g. `revenue` alongside `ROE`). Percentage metrics (ROE, ROCE, net_profit_margin) are already on the same scale and don't need it — the existing `pct_metrics` check handles that correctly.

---

## 8. Refinement MCQ Responses Counted as Clarifications

**Current:** In `agent/agent.py::chat()`, any assistant message containing `"A)"`, `"B)"`, `"C)"` gets appended to `self.clarifications`:
```python
if any(opt in content for opt in ["A)", "B)", "C)"]):
    self.clarifications.append(content[:100])
```

**Problem:** The refinement MCQ (shown after 0 results) also contains `"A)"`, `"B)"` etc., so it gets counted as a clarification and penalizes confidence twice — once via `self.refinements` and again via `self.clarifications`. A query that hit an empty result and adjusted the threshold ends up with an unfairly low confidence score.

**Fix:** Skip appending to `self.clarifications` if the message contains the refinement MCQ signature (e.g. "Would you like to" / "Lower to").

---

## 9. Confidence Floor Masks Heavily Massaged Queries

**Current:** `utils/confidence.py` clamps the score at 0.5 regardless of how many clarifications, retries, or overrides occurred.

**Problem:** A query that needed 5 clarifications, 3 retries, and 2 overrides still reports 0.5 — indistinguishable from a query that needed just one clarification. The floor makes the score meaningless at the low end.

**Fix:** Remove the floor or lower it to 0.0. Let the score reflect reality.

---

## What Stays the Same

- MCQ clarification loop — no change
- Refinement loop on empty results — no change
- `exec()` sandbox for safe code execution — no change
- All outputs saved to `outputs/` (JSON, CSV, code, plot) — no change
- Chain-of-thought logging — extended, not replaced

---

## 10. Agentic Framework — When and Whether to Use LangGraph

**Current system: no framework needed.**

The current loop (1 tool, 2 interrupt points — clarification MCQ and refinement MCQ) is simple enough that the `while True` loop in `chat()` handles it cleanly. Adding LangGraph now would be overhead with no benefit.

**After next-steps 2–4: LangGraph becomes worth it.**

Once granular tools (step 2), pre-execution feasibility via `get_stats` (step 4), and LLM-driven plot decisions (step 3) are implemented, the agent has:
- 4–5 tools
- 3–4 hard interrupt points (clarification, feasibility warning, empty result, plot confirmation)
- Conditional routing between named stages

At that point the `while True` loop becomes a growing tangle of flags and history-scanning heuristics. LangGraph replaces that with an explicit graph where each stage is a node and each decision is an edge.

**Why the "never assume, always involve user" rule makes this more important:**

Every ambiguity, every infeasible condition, every empty result must pause execution and wait for the user — no silent defaults. In LangGraph, these are `interrupt` nodes: compute stops, user is asked, execution only resumes on explicit answer. In the current loop, each pause is a fragile combination of flag detection + early return. As interrupt points grow, that approach breaks down.

**Concrete example of where the loop breaks:**

Suppose the user asks: `"Find companies with PE < 5 AND ROE > 40"`.

With granular tools, the agent would:
1. Call `get_stats("PE")` → min PE in dataset is 8
2. Call `get_stats("ROE")` → max ROE in dataset is 32
3. Detect joint infeasibility — both conditions are outside dataset range simultaneously
4. **Interrupt** → ask user to adjust before spending any compute on execution

In the current `while True` loop, step 3 requires checking tool results mid-loop, branching conditionally, suppressing the next LLM call, injecting a clarification message, and tracking that we're in a "feasibility pause" state — all via flags. With two such interrupt points this is manageable. With four it becomes unmaintainable.

In LangGraph:
```python
# Each stage is just a node, branching is just an edge condition
graph.add_edge("feasibility_check", "clarification", condition=lambda s: s["infeasible"])
graph.add_edge("feasibility_check", "execute", condition=lambda s: not s["infeasible"])
```

The architecture matches the design doc exactly — named stages, typed transitions, explicit interrupt points — instead of being implicit inside a loop.

**Summary:**

| Phase | Framework |
|---|---|
| Current system (1 tool, 2 interrupts) | None — loop is sufficient |
| After steps 2–4 (4+ tools, 3+ interrupts) | LangGraph — loop becomes unmaintainable |

LangChain is not needed at any stage — tool schema, history management, and the exec sandbox are all better hand-rolled for this system.
