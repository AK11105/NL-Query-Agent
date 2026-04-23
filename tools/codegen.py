from data.loader import DATASET
import pandas as pd

def generate_code(q: dict) -> str:
    lines = ["import pandas as pd", "df = DATASET.copy()"]

    # Time filter
    time = q.get("time")
    if time and time.get("type") == "last_n_years":
        n = time["value"]
        lines.append(f"df = df[df['year'] >= df['year'].max() - {n - 1}]")

    # Aggregate per company
    metrics = q.get("metrics", [])
    if metrics:
        agg = {m: "mean" for m in metrics}
        agg_str = "{" + ", ".join(f'"{k}": "mean"' for k in agg) + "}"
        lines.append(f"grouped = df.groupby('company').agg({agg_str}).reset_index()")
    else:
        lines.append("grouped = df.groupby('company').mean(numeric_only=True).reset_index()")

    # Conditions
    filters = []
    for cond in q.get("conditions", []):
        filters.append(f"(grouped['{cond['metric']}'] {cond['op']} {cond['value']})")
    if filters:
        lines.append(f"filtered = grouped[{' & '.join(filters)}]")
    else:
        lines.append("filtered = grouped")

    # Rank / sort
    rank_by = q.get("rank_by")
    rank_asc = q.get("rank_ascending", True)
    limit = q.get("limit", 50)
    if rank_by:
        lines.append(f"result = filtered.sort_values('{rank_by}', ascending={rank_asc}).head({limit})")
    else:
        lines.append(f"result = filtered.head({limit})")

    # Trend data (time series per company)
    intent = q.get("intent", [])
    if "trend" in intent and metrics:
        trend_metric = metrics[0]
        companies_expr = "result['company'].tolist()"
        lines.append(f"trend_df = df[df['company'].isin({companies_expr})][['company','year','{trend_metric}']]")
        lines.append("trend_data = trend_df.pivot(index='year', columns='company', values='" + trend_metric + "').reset_index().to_dict(orient='records')")
    else:
        lines.append("trend_data = []")

    return "\n".join(lines)
