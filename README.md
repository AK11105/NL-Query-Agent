# NL Financial Query Agent

A deep-agent system that interprets natural language financial queries, resolves ambiguity through structured MCQ clarification, and returns deterministic results with visualizations.

---

## Architecture

```
User Query
  → Agent: understand intent, detect ambiguity
  → Clarification loop (MCQ-style, all questions in one message)
  → Pre-execution validation (metric existence, threshold feasibility, derivation check)
  → Code generation + safe execution
  → Result evaluation → refinement loop if empty
  → Plot decision + normalization + rendering
  → Final response (JSON + PNG saved to outputs/)
```

See [`docs/deep-agent-approach.md`](docs/deep-agent-approach.md) for full design and [`docs/deep-agent-example-flow.md`](docs/deep-agent-example-flow.md) for a step-by-step walkthrough.

---

## Project Structure

```
nl-query-agent/
├── agent/
│   ├── agent.py        # NLQueryAgent — LiteLLM tool-calling loop, finalize, output
│   └── prompts.py      # System prompt with MCQ clarification instructions
├── data/
│   └── loader.py       # Synthetic dataset (10 companies × 3 years, 6 metrics)
├── tools/
│   ├── validate.py     # Metric existence, derivation feasibility, threshold checks
│   ├── codegen.py      # Deterministic pandas code generation from structured query
│   ├── execute_query.py# Safe exec wrapper (validate → codegen → exec)
│   └── plot.py         # Plot decision + bar/line rendering with normalization
├── utils/
│   ├── normalize.py    # Min-max normalization + should_normalize logic
│   └── confidence.py   # Confidence score (penalises clarifications/retries/overrides)
├── outputs/            # Auto-created; saves result_*.json + plot_*.png per run
├── main.py             # Entry point
├── test_flow.py        # Full end-to-end simulation (no API key needed)
├── .env.example        # API key template
└── requirements.txt
```

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API key

```bash
cp .env.example .env
# Edit .env and add your key (Groq is the default)
```

### 3. Run without API key (simulation)

```bash
python test_flow.py
```

### 4. Run live agent

```bash
python main.py

# Override model
MODEL=groq/llama-3.3-70b-versatile python main.py
MODEL=gemini/gemini-1.5-flash python main.py
MODEL=openai/gpt-4o python main.py
MODEL=anthropic/claude-3-5-sonnet-20241022 python main.py
```

- Answer the agent's MCQ clarifications during the conversation
- Type `done` when finished — triggers final formatted output + saves to `outputs/`

---

## Available Metrics

| Metric | Description |
|---|---|
| `ROE` | Return on Equity (%) |
| `ROCE` | Return on Capital Employed (%) |
| `net_profit_margin` | Net Profit Margin (%) |
| `PE` | Price-to-Earnings ratio |
| `PB` | Price-to-Book ratio |
| `revenue` | Annual revenue |

---

## Output Format

Each run saves to `outputs/`:
- `result_YYYYMMDD_HHMMSS.json` — full structured result with confidence, clarifications, refinements, data
- `plot_YYYYMMDD_HHMMSS.png` — bar or line chart (normalized where appropriate)

---

## Key Design Decisions

- **No hidden assumptions** — every ambiguous term and threshold is confirmed with the user via MCQ before execution
- **Pre-validation** — metric existence, derivation feasibility, and threshold sanity checked before any compute is spent
- **Self-correcting loop** — empty results trigger a refinement MCQ; overrides are tracked and penalise confidence
- **Deterministic execution** — LLM only reasons; pandas code generation and execution are fully deterministic
- **Normalized plots** — values normalized for comparison charts; raw values used for time-series trends of percentage metrics
