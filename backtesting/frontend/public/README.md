# Visualiser Public Files

Generate the live visualiser data here with:

```bash
python3 scripts/run_backtest.py --strategy examples/momentum_strategy.py --prices data/prices.txt --out frontend/public/results.json
```

The React app fetches `/results.json` and falls back to mock data when this file
is not present.
