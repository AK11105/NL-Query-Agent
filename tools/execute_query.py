import pandas as pd
from data.loader import DATASET
from tools.validate import validate_query
from tools.codegen import generate_code

def execute_query(q: dict) -> dict:
    valid, error = validate_query(q)
    if not valid:
        return {"status": "invalid", "error": error, "row_count": 0}

    code = generate_code(q)
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
