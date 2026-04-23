# Bugs Fixed

---

## From next-steps.md (original design issues)

### 6. Harden `_has_assumed_threshold`
`_HAS_NUMBER` tightened to only match condition-style numbers (`> 20`, `< 5%`); all conditions now checked (not just `conditions[0]`); intercept block finds the first unconfirmed condition.  
**File:** `agent/agent.py`

### 7. `should_normalize` — Trend Was Inverted
`return True` → `return False` for trend intent. Trend charts now show raw values.  
**File:** `utils/normalize.py`

### 8. Refinement MCQ Double-Counted as Clarification
Clarifications append now skipped when message matches refinement signature (`"Would you like to"` + `"Lower to"`).  
**File:** `agent/agent.py`

### 9. Confidence Floor at 0.5
Floor lowered from `0.5` to `0.0`. Score now reflects reality.  
**File:** `utils/confidence.py`

---

## From live run (Apr 23)

### B1. False Refinement MCQ Printed Before Results
After successful tool call with `row_count > 0`, refinement MCQ text is stripped from the LLM response before returning.  
**File:** `agent/agent.py`

### B2. Reasoning Trace Accumulated Across Queries
`self._reasoning` reset after each `finalize()` call so each query gets an isolated trace.  
**File:** `agent/agent.py` (`run()`)

### B3. Results Hard-Capped at 10
`codegen.py` now defaults to 50; `limit` exposed in tool schema so LLM can pass user-specified counts.  
**Files:** `tools/codegen.py`, `agent/agent.py`

### B4. LLM Hallucinated PE as Valid Metric
System prompt now explicitly forbids metrics outside the available list and maps PE → `earnings_yield`.  
**File:** `agent/prompts.py`

### B5. Confidence 0.9 on Zero-Clarification Query
Root cause was B1 (spurious refinement text counted as clarification). Fixed by B1.
