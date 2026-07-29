import argparse
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "algothon-matplotlib"),
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_results(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_days(results: dict) -> list[int]:
    series = results.get("series", {})

    if "days" in series:
        return series["days"]

    return [record["day"] for record in results.get("daily_records", [])]


def save_line_chart(
    days: list[int],
    values: list[float],
    title: str,
    ylabel: str,
    output_path: Path,
) -> None:
    plt.figure(figsize=(10, 5))
    plt.plot(days, values, marker="o", linewidth=2)
    plt.title(title)
    plt.xlabel("Day")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_daily_pnl_chart(
    days: list[int],
    values: list[float],
    output_path: Path,
) -> None:
    colors = ["#1f7a4d" if value >= 0 else "#b42318" for value in values]

    plt.figure(figsize=(10, 5))
    plt.bar(days, values, color=colors)
    plt.axhline(0, color="#333333", linewidth=1)
    plt.title("Daily P&L")
    plt.xlabel("Day")
    plt.ylabel("P&L")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def save_turnover_commission_chart(
    days: list[int],
    turnover: list[float],
    commission: list[float],
    output_path: Path,
) -> None:
    fig, left_axis = plt.subplots(figsize=(10, 5))

    left_axis.plot(days, turnover, marker="o", linewidth=2, label="Turnover")
    left_axis.set_xlabel("Day")
    left_axis.set_ylabel("Turnover")
    left_axis.grid(True, alpha=0.3)

    right_axis = left_axis.twinx()
    right_axis.plot(
        days,
        commission,
        marker="s",
        linewidth=2,
        color="#b45309",
        label="Commission",
    )
    right_axis.set_ylabel("Commission")

    lines = left_axis.get_lines() + right_axis.get_lines()
    labels = [line.get_label() for line in lines]
    left_axis.legend(lines, labels, loc="best")

    plt.title("Turnover And Commission")
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description="Save quick-look PNG charts from an Algothon results JSON."
    )
    parser.add_argument("--results", required=True, help="Path to results JSON.")
    parser.add_argument("--out-dir", required=True, help="Folder for PNG charts.")

    args = parser.parse_args()

    results = load_results(args.results)
    series = results.get("series", {})
    days = get_days(results)
    output_dir = Path(args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    save_line_chart(
        days=days,
        values=series.get("cumulative_pnl", []),
        title="Cumulative P&L",
        ylabel="Cumulative P&L",
        output_path=output_dir / "cumulative_pnl.png",
    )
    save_daily_pnl_chart(
        days=days,
        values=series.get("daily_pnl", []),
        output_path=output_dir / "daily_pnl.png",
    )
    save_line_chart(
        days=days,
        values=series.get("drawdown", []),
        title="Drawdown",
        ylabel="Drawdown",
        output_path=output_dir / "drawdown.png",
    )
    save_turnover_commission_chart(
        days=days,
        turnover=series.get("daily_turnover", []),
        commission=series.get("daily_commission", []),
        output_path=output_dir / "turnover_commission.png",
    )

    print(f"Saved charts to: {output_dir}")


if __name__ == "__main__":
    main()
