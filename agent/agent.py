import json
import litellm
from tools.execute_query import execute_query
from tools.plot import decide_plot, render_plot
from utils.confidence import compute_confidence
from agent.prompts import SYSTEM_PROMPT

# Set litellm.model in env or pass via MODEL env var.
# Examples:
#   MODEL=gemini/gemini-1.5-flash   + GEMINI_API_KEY
#   MODEL=groq/llama3-70b-8192      + GROQ_API_KEY
#   MODEL=openai/gpt-4o             + OPENAI_API_KEY
#   MODEL=anthropic/claude-3-5-sonnet-20241022 + ANTHROPIC_API_KEY

import os
DEFAULT_MODEL = os.environ.get("MODEL", "groq/llama-3.3-70b-versatile")

_TOOL_SCHEMA = [{
    "type": "function",
    "function": {
        "name": "execute_query_tool",
        "description": "Execute a structured financial query against the dataset.",
        "parameters": {
            "type": "object",
            "properties": {
                "metrics":        {"type": "array",  "items": {"type": "string"}, "description": "List of metrics e.g. ['ROE', 'PE']"},
                "conditions":     {"type": "array",  "items": {"type": "object"}, "description": "List of {metric, op, value} filter conditions"},
                "intent":         {"type": "array",  "items": {"type": "string"}, "description": "List of intents: filter, rank, trend"},
                "time":           {"type": "object", "description": "{type: last_n_years, value: int}"},
                "rank_by":        {"type": "string", "description": "Metric to sort results by"},
                "rank_ascending": {"type": "boolean","description": "Sort ascending if true"},
                "limit":          {"type": "integer", "description": "Max rows to return (default 50). Use when user says 'top N' or 'show N'."},
            },
            "required": ["metrics", "conditions", "intent"],
        },
    },
}]


import re

_DONT_KNOW = re.compile(
    r"\b(i don'?t know|not sure|no idea|idk|unsure|doesn'?t matter|don'?t care|whatever|no preference)\b",
    re.IGNORECASE,
)

_QUALITATIVE = re.compile(
    r'\b(high|low|good|best|strong|weak|cheap|expensive|profitable|undervalued|overvalued|quality|solid|top|worst|poor)\b',
    re.IGNORECASE
)
_HAS_NUMBER = re.compile(r'[><=!]=?\s*\d+|\d+\s*%')

def _condition_has_number(user_msg: str, metric: str) -> bool:
    """Return True if the user explicitly gave a numeric threshold for this metric."""
    # Look for the metric name followed (nearby) by a comparison+number, or vice versa
    pattern = re.compile(
        rf'(?:{re.escape(metric)}\s*[><=!]=?\s*\d+|\d+\s*%?\s*[><=!]=?\s*{re.escape(metric)})',
        re.IGNORECASE,
    )
    return bool(pattern.search(user_msg)) or bool(_HAS_NUMBER.search(user_msg) and metric.lower() in user_msg.lower() and not _QUALITATIVE.search(user_msg))

def _has_assumed_threshold(user_msg: str, conditions: list) -> bool:
    """Return True if the LLM assumed a numeric threshold for any qualitative word in the query."""
    if not _QUALITATIVE.search(user_msg):
        return False
    for cond in conditions:
        metric = cond.get("metric", "")
        if not _condition_has_number(user_msg, metric):
            return True  # qualitative word present, no explicit number for this metric
    return False


def _execute_query_tool(**kwargs) -> str:
    return json.dumps(execute_query(kwargs), default=str)


class NLQueryAgent:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.clarifications = []
        self.refinements = []
        self.overrides = 0
        self.last_result = None
        self.last_query = None
        self._reasoning: list[dict] = []   # structured CoT log

    def _log(self, stage: str, observation: str, decision: str):
        self._reasoning.append({"stage": stage, "observation": observation, "decision": decision})

    def _call_llm(self):
        import time
        from litellm.exceptions import RateLimitError, BadRequestError
        for attempt in range(4):
            try:
                return litellm.completion(
                    model=self.model,
                    messages=self.history,
                    tools=_TOOL_SCHEMA,
                    tool_choice="auto",
                ).choices[0].message
            except RateLimitError:
                if attempt == 3:
                    raise
                wait = 2 ** (attempt + 2)
                print(f"[rate limit] retrying in {wait}s...")
                time.sleep(wait)
            except BadRequestError as e:
                if "tool_use_failed" not in str(e) or attempt == 3:
                    raise
                time.sleep(1)

    def _handle_tool_calls(self, msg) -> bool:
        """Returns True if tool was executed, False if intercepted for clarification."""
        self.history.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)

            # Guard: if user used qualitative words and LLM assumed a threshold, intercept
            last_user = next(
                (m["content"] for m in reversed(self.history) if m["role"] == "user"), ""
            )
            if _has_assumed_threshold(last_user, args.get("conditions", [])):
                # Remove the tool call from history and ask instead
                self.history.pop()
                # Find the first condition the user didn't explicitly number
                assumed_cond = next(
                    (c for c in args.get("conditions", []) if not _condition_has_number(last_user, c.get("metric", ""))),
                    args["conditions"][0],
                )
                metric = assumed_cond["metric"]
                assumed = assumed_cond["value"]
                clarification = (
                    f'What {metric} threshold defines "{_QUALITATIVE.search(last_user).group()}"?\n'
                    f'A) > {int(assumed * 0.5)}\n'
                    f'B) > {assumed}\n'
                    f'C) > {int(assumed * 1.5)}\n'
                    f'D) Custom'
                )
                self.history.append({"role": "assistant", "content": clarification})
                self.clarifications.append(clarification[:100])
                self._log(
                    "ambiguity_detected",
                    f"LLM assumed {metric} > {assumed} from qualitative word in query.",
                    "Intercepted tool call — asking user for explicit threshold."
                )
                return False

            self._log(
                "query_execution",
                f"Resolved query: metrics={args.get('metrics')}, "
                f"conditions={args.get('conditions')}, intent={args.get('intent')}, "
                f"time={args.get('time')}, rank_by={args.get('rank_by')}",
                "Calling execute_query_tool with structured parameters."
            )
            result_str = _execute_query_tool(**args)
            self.last_query = args
            self.last_result = json.loads(result_str)
            row_count = self.last_result.get("row_count", 0)
            status    = self.last_result.get("status", "unknown")
            self._log(
                "execution_result",
                f"Tool returned status={status}, row_count={row_count}.",
                "Proceeding to evaluate result quality." if row_count > 0
                else "Result is empty — will trigger refinement loop."
            )
            self.history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })
        return True

    def chat(self, user_message: str) -> str:
        # Detect if this is a refinement response
        is_refinement = any(
            "Would you like to" in (m.get("content") or "") and "Lower to" in (m.get("content") or "")
            for m in self.history[-3:] if m["role"] == "assistant"
        )
        if is_refinement:
            self.overrides += 1
            self.refinements.append(user_message.strip())
            self._log(
                "threshold_refinement",
                f"Empty result triggered refinement MCQ. User chose: '{user_message.strip()}'.",
                "Updating threshold and re-executing query."
            )

        # Detect if this is answering a clarification MCQ
        is_clarification = any(
            any(opt in (m.get("content") or "") for opt in ["A)", "B)", "C)"])
            for m in self.history[-3:] if m["role"] == "assistant"
        ) and not is_refinement

        if is_clarification:
            self._log(
                "clarification_received",
                f"User answered clarification: '{user_message.strip()}'.",
                "Resolving ambiguous terms and thresholds from user response."
            )
            # Block non-answers from reaching the LLM
            if _DONT_KNOW.search(user_message):
                last_clarification = next(
                    (m["content"] for m in reversed(self.history) if m["role"] == "assistant"),
                    ""
                )
                reply = (
                    "I need a specific value to run the query — please pick one of the options above.\n\n"
                    + last_clarification
                )
                self.history.append({"role": "user", "content": user_message})
                self.history.append({"role": "assistant", "content": reply})
                return reply

        self.history.append({"role": "user", "content": user_message})

        # Log the initial query understanding on first user turn
        if len([m for m in self.history if m["role"] == "user"]) == 1:
            self._log(
                "query_understanding",
                f"Received query: '{user_message.strip()}'.",
                "Parsing intent, identifying metrics and time range, detecting ambiguous terms."
            )

        while True:
            msg = self._call_llm()
            if msg.tool_calls:
                executed = self._handle_tool_calls(msg)
                if not executed:
                    # intercepted — clarification already appended, return it
                    return self.history[-1]["content"]
                continue
            content = msg.content or ""
            # If tool just ran successfully with results, suppress any spurious refinement MCQ
            if (self.last_result and self.last_result.get("row_count", 0) > 0
                    and "Would you like to" in content and "Lower to" in content):
                # Strip the refinement block — keep only the insight text before it
                content = content[:content.index("Would you like to")].strip()
            self.history.append({"role": "assistant", "content": content})
            is_refinement_msg = "Would you like to" in content and "Lower to" in content
            if any(opt in content for opt in ["A)", "B)", "C)"]) and not is_refinement_msg:
                self.clarifications.append(content[:100])
                self._log(
                    "ambiguity_detected",
                    "Query contains undefined terms or missing thresholds.",
                    "Generating MCQ clarification to resolve before execution."
                )
            return content

    def finalize(self) -> dict:
        if not self.last_result or self.last_result.get("status") != "success":
            return {"status": "no_result"}

        import csv, textwrap
        from datetime import datetime
        from utils.normalize import should_normalize

        result   = self.last_result.get("result", [])
        trend    = self.last_result.get("trend_data", [])
        intent   = (self.last_query or {}).get("intent", [])
        metrics  = (self.last_query or {}).get("metrics", [])
        y_metric = metrics[0] if metrics else "ROE"

        os.makedirs("outputs", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # --- chain of thought ---
        chain_of_thought = self._reasoning

        # --- save query code ---
        query_code = self.last_result.get("code", "")
        query_code_path = f"outputs/query_{ts}.py"
        with open(query_code_path, "w") as f:
            f.write("# Auto-generated query code\nfrom data.loader import DATASET\nimport pandas as pd\n\n")
            body = "\n".join(
                l for l in query_code.splitlines()
                if not l.startswith("import ") and not l.startswith("from ")
            )
            f.write(body + "\n")

        # --- plot ---
        plot_dec  = decide_plot(intent, len(result))
        self._log(
            "visualization_decision",
            f"intent={intent}, row_count={len(result)}, y_metric={y_metric}.",
            f"Selected plot_type='{plot_dec.get('plot_type')}': {plot_dec.get('reason')}."
        )
        plot_path = None
        plot_code_path = None
        if plot_dec.get("should_plot"):
            plot_path = render_plot(
                plot_dec, result, trend,
                x_metric="company", y_metric=y_metric,
                intent=intent, title=f"Results — {y_metric}",
            )
            plot_type = plot_dec.get("plot_type", "bar")
            do_norm   = should_normalize(intent, y_metric)
            plot_code_path = f"outputs/plot_{ts}.py"
            lines = [
                "# Auto-generated plot code",
                "import matplotlib; matplotlib.use('Agg')",
                "import matplotlib.pyplot as plt, json",
                "from utils.normalize import normalize, should_normalize",
                f"with open('outputs/result_{ts}.json') as f: data = json.load(f)",
                "result = data['data']; trend_data = data.get('trend_data', [])",
                f"intent = {intent!r}; y_metric = {y_metric!r}; do_norm = {do_norm!r}",
                "fig, ax = plt.subplots(figsize=(10, 5))",
            ]
            if plot_type == "line":
                lines += [
                    "companies = [k for k in trend_data[0].keys() if k != 'year'] if trend_data else []",
                    "years = [row['year'] for row in trend_data]",
                    "for c in companies:",
                    "    vals = [row.get(c, 0) for row in trend_data]",
                    "    if do_norm: vals = normalize(vals)",
                    "    ax.plot(years, vals, marker='o', label=c)",
                    "ax.set_xlabel('Year'); ax.set_ylabel(y_metric); ax.legend(fontsize=7)",
                ]
            else:
                lines += [
                    "companies = [r['company'] for r in result]",
                    "vals = [r.get(y_metric, 0) for r in result]",
                    "if do_norm: vals = normalize(vals)",
                    "ax.bar(companies, vals)",
                    "ax.set_xlabel('Company'); ax.set_ylabel(y_metric)",
                    "plt.xticks(rotation=30, ha='right')",
                ]
            lines += [
                f"ax.set_title('Results — {y_metric}')",
                "plt.tight_layout()",
                f"plt.savefig('outputs/plot_{ts}.png'); plt.close()",
            ]
            with open(plot_code_path, "w") as f:
                f.write("\n".join(lines) + "\n")

        # --- save CSV ---
        csv_path = None
        if result:
            csv_path = f"outputs/results_{ts}.csv"
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=result[0].keys())
                writer.writeheader()
                writer.writerows(result)

        final = {
            "status":           "success",
            "summary":          f"{len(result)} companies found",
            "confidence":       compute_confidence(len(self.clarifications), len(self.refinements), self.overrides),
            "clarifications":   self.clarifications,
            "refinements":      self.refinements,
            "chain_of_thought": chain_of_thought,
            "visualization":    {**plot_dec, "plot_saved_to": plot_path},
            "data":             result,
            "trend_data":       trend,
        }

        json_path = f"outputs/result_{ts}.json"
        with open(json_path, "w") as f:
            json.dump(final, f, indent=2, default=str)

        final["_saved_to"] = {
            "json":       json_path,
            "csv":        csv_path,
            "query_code": query_code_path,
            "plot_code":  plot_code_path,
        }
        return final


def _print_final(final: dict):
    if final.get("status") == "no_result":
        return

    sep  = "─" * 55
    sep2 = "═" * 55

    data = final.get("data", [])
    if data:
        print(f"\n  Results  ({len(data)} companies)")
        print(f"  {sep}")
        keys = list(data[0].keys())
        col_w = 20
        print("  " + "  ".join(k.ljust(col_w) for k in keys))
        print("  " + "  ".join("-" * col_w for _ in keys))
        for row in data:
            print("  " + "  ".join(
                str(round(v, 2) if isinstance(v, float) else v).ljust(col_w)
                for v in row.values()
            ))
        print(f"  {sep}")

    viz = final.get("visualization", {})
    if viz.get("should_plot") and viz.get("plot_saved_to"):
        print(f"\n  Plot saved  : {viz['plot_saved_to']}  ({viz.get('plot_type')} chart)")

    cot = final.get("chain_of_thought", [])
    if cot:
        print(f"\n  Reasoning Trace")
        print(f"  {sep}")
        stage_labels = {
            "query_understanding":    "Query Understanding",
            "ambiguity_detected":     "Ambiguity Detected",
            "clarification_received": "Clarification Received",
            "query_execution":        "Query Execution",
            "execution_result":       "Execution Result",
            "threshold_refinement":   "Threshold Refinement",
            "visualization_decision": "Visualization Decision",
        }
        for i, step in enumerate(cot, 1):
            label = stage_labels.get(step.get("stage", ""), step.get("stage", ""))
            print(f"\n  [{i}] {label}")
            print(f"      Observed : {step.get('observation', '')}")
            print(f"      Decision : {step.get('decision', '')}")

    saved = final.get("_saved_to", {})
    if any(saved.values()):
        print(f"\n  Saved  : " + "  |  ".join(
            f"{k}: {v}" for k, v in saved.items() if v
        ))

    conf = final.get("confidence")
    if conf is not None:
        print(f"  Confidence : {conf}")
    print()


def run():
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    agent = NLQueryAgent(model=model)

    W = 60
    print(f"\n  {'NL Financial Query Agent':^{W}}")
    print(f"  {'Model: ' + model:^{W}}")
    print(f"  {('─' * W)}")
    print(f"  Type your query below. Ctrl+C or 'exit' to quit.\n")

    while True:
        # prompt
        try:
            user_input = input("\033[1;36m  You\033[0m  ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye.\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("\n  Goodbye.\n")
            raise SystemExit(0)

        print(f"\033[1;32m  Agent\033[0m  ", end="", flush=True)
        response = agent.chat(user_input)
        print(response)

        # auto-finalize whenever a successful result exists
        if agent.last_result and agent.last_result.get("status") == "success" and agent.last_result.get("row_count", 0) > 0:
            final = agent.finalize()
            _print_final(final)
            # reset so we don't re-print on next turn unless a new query runs
            agent.last_result = None
            agent._reasoning = []
