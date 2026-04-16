import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os
from utils.normalize import normalize, should_normalize

def decide_plot(intent: list, row_count: int) -> dict:
    if "trend" in intent:
        return {"should_plot": True, "plot_type": "line", "reason": "trend comparison across companies"}
    if "rank" in intent and row_count > 0:
        return {"should_plot": True, "plot_type": "bar", "reason": "ranking comparison"}
    if row_count > 0:
        return {"should_plot": True, "plot_type": "bar", "reason": "result comparison"}
    return {"should_plot": False, "reason": "no data"}

def render_plot(plot_decision: dict, result: list, trend_data: list,
                x_metric: str, y_metric: str, intent: list, title: str = "Results") -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    plot_type = plot_decision.get("plot_type", "bar")
    do_norm = should_normalize(intent, y_metric)

    if plot_type == "line" and trend_data:
        companies = [k for k in trend_data[0].keys() if k != "year"]
        years = [row["year"] for row in trend_data]
        for company in companies:
            vals = [row.get(company, 0) for row in trend_data]
            if do_norm:
                vals = normalize(vals)
            ax.plot(years, vals, marker="o", label=company)
        ax.set_xlabel("Year")
        ax.set_ylabel(f"{y_metric} (normalized)" if do_norm else y_metric)
        ax.legend(fontsize=7)
    else:
        companies = [r["company"] for r in result]
        vals = [r.get(y_metric, 0) for r in result]
        if do_norm:
            vals = normalize(vals)
        ax.bar(companies, vals)
        ax.set_xlabel("Company")
        ax.set_ylabel(f"{y_metric} (normalized)" if do_norm else y_metric)
        plt.xticks(rotation=30, ha="right")

    ax.set_title(title)
    plt.tight_layout()
    os.makedirs("outputs", exist_ok=True)
    from datetime import datetime
    path = f"outputs/plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(path)
    plt.close()
    return path
