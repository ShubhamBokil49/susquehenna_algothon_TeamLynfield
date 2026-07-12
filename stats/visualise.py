import pandas as pd
import matplotlib.pyplot as plt

# load the stats you already saved
stats = pd.read_csv("asset_stats.csv", index_col=0)

# --- Bar chart: volatility per asset ---
plt.figure(figsize=(14, 6))
stats["volatility"].sort_values(ascending=False).plot(kind="bar")
plt.title("Volatility by asset")
plt.ylabel("Daily volatility")
plt.tight_layout()
plt.savefig("volatility_bar.png", dpi=100)
plt.show()

# --- Bar chart: average daily return per asset ---
plt.figure(figsize=(14, 6))
stats["avg_daily_return"].sort_values(ascending=False).plot(kind="bar", color="green")
plt.title("Average daily return by asset")
plt.ylabel("Avg daily return")
plt.tight_layout()
plt.savefig("avg_return_bar.png", dpi=100)
plt.show()

# --- Bar chart: reward-to-risk per asset ---
plt.figure(figsize=(14, 6))
stats["reward_to_risk"].sort_values(ascending=False).plot(kind="bar", color="purple")
plt.title("Reward-to-risk by asset")
plt.ylabel("Return / Volatility")
plt.tight_layout()
plt.savefig("reward_to_risk_bar.png", dpi=100)
plt.show()

# --- Scatter: return vs volatility, labeled by ticker ---
plt.figure(figsize=(10, 8))
plt.scatter(stats["volatility"], stats["avg_daily_return"])
for ticker, row in stats.iterrows():
    plt.annotate(ticker, (row["volatility"], row["avg_daily_return"]), fontsize=7)
plt.xlabel("Volatility")
plt.ylabel("Avg daily return")
plt.title("Return vs Risk per asset")
plt.axhline(0, color="black", linewidth=0.5)
plt.tight_layout()
plt.savefig("return_vs_risk_scatter.png", dpi=100)
plt.show()