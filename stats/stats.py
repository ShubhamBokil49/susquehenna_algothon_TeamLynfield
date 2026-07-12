import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 1. Load the data
# ---------------------------------------------------------
df = pd.read_csv("prices.txt", sep=r"\s+")
print("Shape (days, assets):", df.shape)

# ---------------------------------------------------------
# 2. Compute daily returns (% change day to day)
# ---------------------------------------------------------
returns = df.pct_change().dropna()

# ---------------------------------------------------------
# 3. Basic stats per asset: average return & volatility
# ---------------------------------------------------------
stats = pd.DataFrame({
    "avg_daily_return": returns.mean(),
    "volatility": returns.std(),
})
stats["reward_to_risk"] = stats["avg_daily_return"] / stats["volatility"]
stats = stats.sort_values("volatility", ascending=False)

print("\n--- Per-asset stats ---")
print(stats)

# ---------------------------------------------------------
# 4. Correlation between assets
# ---------------------------------------------------------
corr = returns.corr()

plt.figure(figsize=(12, 10))
plt.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)
plt.colorbar(label="correlation")
plt.title("Correlation between assets")
plt.savefig("correlation_heatmap.png", dpi=100)
plt.show()

# ---------------------------------------------------------
# 5. Save everything to a CSV so you can look closer
# ---------------------------------------------------------
stats.to_csv("asset_stats.csv")
corr.to_csv("correlation_matrix.csv")

print("\nSaved: asset_stats.csv, correlation_matrix.csv, correlation_heatmap.png")