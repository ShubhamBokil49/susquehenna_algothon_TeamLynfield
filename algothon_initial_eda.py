from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

PRICES_FILE = Path("prices.txt")
OUTPUT_DIR = Path("eda_outputs")
ASSET_CHART_DIR = OUTPUT_DIR / "asset_price_charts"

OUTPUT_DIR.mkdir(exist_ok=True)
ASSET_CHART_DIR.mkdir(exist_ok=True)

prices = pd.read_csv(PRICES_FILE, sep=r"\s+")
prices.index = pd.RangeIndex(start=1, stop=len(prices) + 1, name="Day")

assert prices.shape[1] == 51, f"Expected 51 assets, found {prices.shape[1]}"
assert not prices.isna().any().any(), "Missing prices found"
assert (prices > 0).all().all(), "Zero or negative prices found"

returns = prices.pct_change()
log_returns = np.log(prices / prices.shift(1))
normalised = prices.div(prices.iloc[0]).mul(100)

summary = pd.DataFrame({
    "start_price": prices.iloc[0],
    "end_price": prices.iloc[-1],
    "total_return_pct": (prices.iloc[-1] / prices.iloc[0] - 1) * 100,
    "mean_daily_return_pct": returns.mean() * 100,
    "daily_vol_pct": returns.std() * 100,
    "annualised_vol_pct": returns.std() * np.sqrt(250) * 100,
    "min_price": prices.min(),
    "max_price": prices.max(),
    "max_drawdown_pct": (prices / prices.cummax() - 1).min() * 100,
    "positive_days_pct": (returns > 0).mean() * 100,
    "lag1_return_autocorr": returns.apply(lambda s: s.autocorr(lag=1)),
})
summary.index = summary.index.rename("asset")
summary.to_csv(OUTPUT_DIR / "asset_summary.csv")

corr = log_returns.corr()
upper_mask = np.triu(np.ones(corr.shape), k=1).astype(bool)
pair_corr = (
    corr.where(upper_mask)
    .stack()
    .rename_axis(index=["asset_1", "asset_2"])
    .reset_index(name="return_correlation")
    .sort_values("return_correlation", ascending=False)
)
pair_corr.to_csv(OUTPUT_DIR / "pairwise_return_correlations.csv", index=False)

plt.figure(figsize=(16, 9))
for asset in normalised.columns:
    plt.plot(normalised.index, normalised[asset], linewidth=0.9, alpha=0.65)
plt.axhline(100, linewidth=1)
plt.title("All 51 assets normalised to 100 on Day 1")
plt.xlabel("Day")
plt.ylabel("Normalised price")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "all_assets_normalised.png", dpi=180)
plt.close()

for asset in prices.columns:
    series = normalised[asset]
    plt.figure(figsize=(11, 5.5))
    plt.plot(series.index, series, label="Normalised price", linewidth=1.4)
    plt.plot(series.index, series.rolling(20).mean(), label="20-day moving average", linewidth=1.0)
    plt.plot(series.index, series.rolling(60).mean(), label="60-day moving average", linewidth=1.0)
    plt.axhline(100, linewidth=0.8)
    plt.title(f"{asset}: normalised price path")
    plt.xlabel("Day")
    plt.ylabel("Day 1 = 100")
    plt.legend()
    plt.tight_layout()
    plt.savefig(ASSET_CHART_DIR / f"{asset}_price.png", dpi=150)
    plt.close()

for column, title, xlabel, filename in [
    ("total_return_pct", "Total return over 500 days", "Total return (%)", "ranked_total_returns.png"),
    ("annualised_vol_pct", "Annualised volatility", "Annualised volatility (%)", "ranked_annualised_volatility.png"),
    ("max_drawdown_pct", "Maximum drawdown over 500 days", "Maximum drawdown (%)", "ranked_max_drawdown.png"),
]:
    ranked = summary[column].sort_values()
    plt.figure(figsize=(12, 11))
    plt.barh(ranked.index, ranked.values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Asset")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=180)
    plt.close()

plt.figure(figsize=(15, 13))
image = plt.imshow(corr.values, aspect="auto", vmin=-1, vmax=1)
plt.colorbar(image, label="Correlation")
plt.xticks(range(len(corr.columns)), corr.columns, rotation=90, fontsize=7)
plt.yticks(range(len(corr.index)), corr.index, fontsize=7)
plt.title("Daily log-return correlation matrix")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "return_correlation_heatmap.png", dpi=180)
plt.close()

print(f"Loaded {prices.shape[0]} days and {prices.shape[1]} assets.")
print(f"EDA outputs saved to: {OUTPUT_DIR.resolve()}")
print("\nTop five total returns:")
print(summary["total_return_pct"].nlargest(5).round(2))
print("\nBottom five total returns:")
print(summary["total_return_pct"].nsmallest(5).round(2))