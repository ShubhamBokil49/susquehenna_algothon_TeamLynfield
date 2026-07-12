import pandas as pd
import matplotlib.pyplot as plt

# load the data (tickers as columns, one row per day)
df = pd.read_csv("prices.txt", sep=r"\s+")

print(df.shape)   # (num_days, num_assets)
print(df.head())  # first few rows

# plot every asset's price over time, all on separate small charts
df.plot(subplots=True, layout=(9, 6), figsize=(20, 22), legend=False, title=list(df.columns))
plt.tight_layout()
plt.savefig("all_prices.png", dpi=100)
plt.show()