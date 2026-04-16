# 🧠 FINAL SYSTEM DESIGN: NL FINANCIAL QUERY AGENT

---

## 1. Core Philosophy

> **LLM for reasoning, minimal deterministic layers for correctness, Deep Agent for intelligent orchestration**
> 

This system is designed to:

- Interpret natural language financial queries
- Eliminate implicit assumptions via explicit clarification
- Perform multi-step reasoning using agent-based decomposition
- Prevent invalid execution through pre-validation
- Execute queries deterministically and safely
- Improve robustness through self-correcting agent loops
- Use structured clarification (MCQ-style) to resolve ambiguity
- Ensure thresholds are explicitly defined by the user
- Produce interpretable outputs using normalized values where needed

---

## 2. System Overview

### 🔷 High-Level Architecture

```
User Query
   ↓
Deep Agent (Reasoning Controller)

   → Understand intent
   → Detect ambiguity
   → Generate structured clarifications (MCQ-style)

   ↓
User Clarification Loop
   ↓
Agent Refines Query (explicit thresholds)

   ↓
Pre-Execution Validation Layer

   → Metric existence check
   → Derivation feasibility
   → Threshold validation

   ↓
Execution Engine (Deterministic Tool)

   → Generate code
   → Execute safely

   ↓
Agent Evaluation

   → Analyze result quality
   → Refine / Retry if needed

   ↓
Agent Interpretation + Visualization Decision

   ↓
Final Response
```

---

## 3. Key Design Shift

### Before (Earlier Deep Agent Approach)

- Intelligence embedded inside a single tool
- Agent primarily handled retries
- Implicit assumptions in metric resolution
- Execution-first workflow
- Limited decomposition

---

### After (Updated Approach)

- Agent is the primary reasoning engine
- No implicit assumptions — all ambiguity clarified
- Clarification is structured and user-guided
- Thresholds are explicitly defined by the user
- Pre-validation prevents invalid execution
- Explicit task decomposition for complex queries
- Self-correcting loop with intelligent refinement
- Execution engine simplified to deterministic operations

---

## 4. Execution Engine (Deterministic Tool)

The pipeline is a **pure execution tool**, with no embedded reasoning.

---

### 4.1 Function Signature

```python
def execute_query(structured_query: dict) -> dict:
```

---

### 4.2 Internal Flow

```
Structured Query
 ↓
1. Minimal Validation
 ↓
2. Code Generation (LLM-constrained)
 ↓
3. Safe Execution
 ↓
Return Result
```

---

### 4.3 Implementation

```python
def execute_query(q):

    valid, error = validate_basic(q)
    if not valid:
        return {"status": "invalid", "error": error}

    code = generate_code(q)
    result, exec_error = execute(code)

    return {
        "status": "success" if exec_error is None else "error",
        "result": result,
        "error": exec_error
    }
```

---

## 5. Pre-Execution Validation Layer (Hybrid)

This layer ensures **only meaningful queries reach execution**, reducing wasted compute.

---

### 5.1 Metric Existence Check (Deterministic)

- Verifies that requested metrics exist in dataset

---

### 5.2 Derivation Feasibility (Hybrid)

- Detects if missing metrics can be computed
- LLM proposes formula
- User confirms before execution

---

### 5.3 Threshold Validation

- Ensures all thresholds are explicitly defined by the user
- Prevents implicit assumptions based on dataset

---

### 5.4 Data-Aware Feasibility Check (Hybrid)

- Compares user-defined thresholds against dataset distribution
- Flags unrealistic conditions
- Suggests alternatives instead of rejecting

---

### Example

```
User: ROE > 50%

System:
"This threshold is very restrictive based on dataset distribution.
Would you like to:
A) Keep it
B) Lower to 20%
C) View distribution first"
```

---

## 6. Deep Agent Layer

The Deep Agent is responsible for **all reasoning and orchestration**.

---

### 6.1 Responsibilities

- Query understanding
- Ambiguity detection
- MCQ-based clarification generation
- Threshold elicitation
- Task decomposition
- Pre-validation reasoning
- Result evaluation
- Query refinement
- Interpretation and explanation
- Visualization decision

---

### 6.2 Agent Creation

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    tools=[execute_query],
    system_prompt="""
    You are a financial analysis assistant.

    - Understand and clarify queries before execution
    - Use structured multiple-choice clarifications where possible
    - Avoid assumptions; always confirm thresholds with user
    - Decompose complex tasks into steps
    - Validate feasibility before execution
    - Refine queries if results are empty or invalid
    - Provide clear financial insights
    """
)
```

---

### 6.3 Execution

```python
agent.invoke({
    "messages": [
        {"role": "user", "content": "Find good companies and rank by valuation"}
    ]
})
```

---

## 7. Core Components

---

### 7.1 Query Understanding (LLM)

Extracts:

```json
{
  "raw_terms": ["good", "valuation"],
  "intent": ["filter", "rank"]
}
```

---

### 7.2 Ambiguity Detection (LLM)

Identifies underspecified terms and missing thresholds.

---

### 7.3 Clarification Loop

Clarifications are structured and interactive.

Example:

```
What defines "good companies"?

A) High ROE
B) High Revenue Growth
C) Low Debt
D) Custom
```

Threshold selection:

```
What ROE threshold should be used?

A) > 10%
B) > 15%
C) > 20%
D) Custom
```

---

### 7.4 Task Decomposition (LLM)

Breaks query into steps:

```
1. Filter companies by profitability
2. Rank by valuation
3. Return top results
```

---

### 7.5 Code Generation (Hybrid)

- LLM generates pandas code
- Constrained by structured query and dataset

---

### 7.6 Safe Execution (Deterministic)

Ensures reliable execution without side effects.

---

### 7.7 Self-Correcting Loop (Hybrid)

```
Execute → Evaluate → Refine → Re-execute
```

---

### 7.8 Interpretation (LLM)

Generates financial insights based on results.

---

### 7.9 Plot Controller

---

### Plot Decision (LLM)

LLM determines:

```python
plot_decision = {
    "should_plot": bool,
    "plot_type": "bar" | "scatter" | "line" | "histogram",
    "x_axis": str,
    "y_axis": str,
    "grouping": str | None,
    "reason": str
}
```

---

### Value Normalization

Values are normalized when needed to improve interpretability.

```python
def normalize(values):
    return (values - min(values)) / (max(values) - min(values))
```

---

### When Normalization is Applied

| Scenario | Normalize |
| --- | --- |
| comparing entities | Yes |
| ranking metrics | Yes |
| time series trends | No |
| percentage metrics | No |

---

### Plot Payload

```python
plot_payload = {
    "type": plot_type,
    "x": data[x_axis],
    "y": normalized_values if normalize else raw_values,
    "normalized": normalize,
    "title": str
}
```

---

### Rendering

Plot generation is deterministic and separate from LLM reasoning.

---

## 8. Agent Behavior (Example)

### Query:

> “Find good companies”
> 

---

### Step 1 — Ambiguity detected

---

### Step 2 — Clarification

```
What defines "good"?

A) High ROE
B) High Growth
C) Low Debt
D) Custom
```

---

### Step 3 — Threshold Selection

```
What threshold?

A) >10%
B) >20%
C) Custom
```

---

### Step 4 — Pre-validation

- Metric existence verified
- Threshold validated

---

### Step 5 — Execution

---

### Step 6 — Visualization

- Comparison plot generated with normalized values

---

### Step 7 — Interpretation

Agent explains results in financial terms.

---

## 9. Confidence Engine

---

### Factors

- Number of clarifications
- Number of refinements
- Execution success
- Threshold overrides

---

### Implementation

```python
def compute_confidence(clarifications, retries, overrides):

    score = 1.0
    score -= 0.1 * clarifications
    score -= 0.1 * retries
    score -= 0.05 * overrides

    return max(score, 0.5)
```

---

## 10. Final Response Format

```python
{
  "status": "success",
  "summary": "5 companies found",
  "insight": "...",
  "confidence": 0.82,

  "clarifications": [...],

  "thresholds": {
    "roe": ">20%"
  },

  "refinements": [...],

  "visualization": {
    "type": "bar",
    "normalized": True,
    "reason": "comparison across companies"
  },

  "data": [...]
}
```

---

## 11. Key Advantages

- Eliminates hidden assumptions
- Structured clarification reduces ambiguity
- User-controlled thresholds improve trust
- Prevents invalid execution before compute is spent
- Enables complex multi-step reasoning
- Maintains deterministic reliability
- Produces interpretable and explainable outputs
- Normalized visualizations improve comparison clarity
- Scales without rule explosion

---

## 12. Implementation Roadmap

1. Remove assumption-based metric resolution
2. Implement structured clarification flow
3. Add MCQ-based clarification templates
4. Add threshold elicitation layer
5. Build pre-validation layer
6. Simplify execution engine
7. Add evaluation and refinement loop
8. Implement visualization decision logic
9. Add normalization layer for plots

---

## 13. Final System Summary

> **An agent-driven financial reasoning system where ambiguity is resolved through structured clarification, thresholds are explicitly defined by the user, and results are presented with normalized, interpretable visualizations—ensuring correctness, transparency, and intelligent decision-making.**
> 

---