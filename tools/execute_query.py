import os
import json
import pandas as pd
import litellm
from data.loader import DATASET
from tools.validate import validate_query
from agent.prompts import CODEGEN_PROMPT

DEFAULT_MODEL = os.environ.get("MODEL", "groq/llama-3.3-70b-versatile")


def _llm_generate_code(q: dict) -> str:
    user_msg = f"Query specification (JSON):\n{json.dumps(q, indent=2)}\n\nWrite the pandas code."
    resp = litellm.completion(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": CODEGEN_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0,
    )
    code = resp.choices[0].message.content.strip()
    # Strip markdown fences if the model adds them anyway
    if code.startswith("```"):
        code = "\n".join(
            line for line in code.splitlines()
            if not line.startswith("```")
        ).strip()
    return code


def execute_query(q: dict) -> dict:
    valid, error = validate_query(q)
    if not valid:
        return {"status": "invalid", "error": error, "row_count": 0}

    code = _llm_generate_code(q)
    ns = {"DATASET": DATASET, "pd": pd}
    try:
        exec(compile(code, "<codegen>", "exec"), ns)
        result_df  = ns.get("result", pd.DataFrame())
        trend_data = ns.get("trend_data", [])
        return {
            "status":     "success",
            "result":     result_df.to_dict(orient="records"),
            "trend_data": trend_data,
            "row_count":  len(result_df),
            "code":       code,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "code": code, "row_count": 0}
