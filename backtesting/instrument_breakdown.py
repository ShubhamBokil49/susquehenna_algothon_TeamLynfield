import json
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

RESULTS_PATH = sys.argv[1] if len(sys.argv) > 1 else "examples/sample_results.json"
PRICES_PATH = sys.argv[2] if len(sys.argv) > 2 else "data/prices.txt"
OUT_DIR = sys.argv[3] if len(sys.argv) > 3 else "examples/plots"

with open(RESULTS_PATH) as f:
    results = json.load(f)

df = pd.DataFrame(results["instrument_summary"])

try:
    with open(PRICES_PATH) as f:
        tickers = f.readline().split()
    df["ticker"] = df["instrument"].map(lambda i: tickers[i] if i < len(tickers) else f"#{i}")
except FileNotFoundError:
    print(f"Warning: couldn't find {PRICES_PATH} to map ticker names, using raw indices instead.")
    df["ticker"] = df["instrument"]

df = df.sort_values("total_pnl", ascending=False)

pd.set_option("display.max_rows", None)
pd.set_option("display.width", 160)

cols = ["ticker", "instrument", "total_pnl", "total_trades", "total_turnover",
        "total_commission", "average_position", "max_abs_position",
        "best_day_pnl", "worst_day_pnl"]
print(df[cols].to_string(index=False))

os.makedirs(OUT_DIR, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 6))
colors = ["green" if v >= 0 else "red" for v in df["total_pnl"]]
ax.bar(df["ticker"], df["total_pnl"], color=colors)
ax.set_ylabel("Total P&L ($)")
ax.set_title("P&L by instrument")
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/pnl_by_instrument.png", dpi=150)
print(f"\nSaved chart to {OUT_DIR}/pnl_by_instrument.png")

fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(df["ticker"], df["total_turnover"], color="steelblue")
ax.set_ylabel("Total turnover ($)")
ax.set_title("Turnover by instrument")
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/turnover_by_instrument.png", dpi=150)
print(f"Saved chart to {OUT_DIR}/turnover_by_instrument.png")

fig, ax = plt.subplots(figsize=(14, 6))
ax.bar(df["ticker"], df["total_commission"], color="darkorange")
ax.set_ylabel("Total commission ($)")
ax.set_title("Commission paid by instrument")
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig(f"{OUT_DIR}/commission_by_instrument.png", dpi=150)
print(f"Saved chart to {OUT_DIR}/commission_by_instrument.png")

df[cols].to_csv(f"{OUT_DIR}/instrument_summary.csv", index=False)
print(f"Saved full table to {OUT_DIR}/instrument_summary.csv")

active = df[df["total_trades"] > 0]
print(f"\n{len(active)} of {len(df)} instruments were traded at all.")
print(f"Total P&L across all instruments: {df['total_pnl'].sum():.2f}")
print(f"Total commission paid: {df['total_commission'].sum():.2f}")