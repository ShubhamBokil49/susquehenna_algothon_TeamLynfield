from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ============================================================
# CONFIGURATION
# ============================================================

TEST_DAYS = 200
CV_SPLITS = 5

# ALGO is excluded as a prediction target because it is the basket.
# It is still allowed to be used as a predictor.
EXCLUDED_TARGETS = ["ALGO"]

# Candidate numbers of principal components.
# The script automatically removes values larger than the feature count.
COMPONENT_CANDIDATES = [
    1,
    2,
    3,
    5,
    8,
    10,
    15,
    20,
    30,
    40,
    50,
]

# Set this above zero later to test transaction costs.
# Example: 0.0005 means 0.05% per unit of position turnover.
TRANSACTION_COST = 0.0


# ============================================================
# LOAD DATA
# ============================================================

possible_paths = [
    Path.cwd() / "prices.txt",
    Path.cwd().parent / "prices.txt",
]

if "__file__" in globals():
    script_directory = Path(__file__).resolve().parent

    possible_paths.extend([
        script_directory / "prices.txt",
        script_directory.parent / "prices.txt",
    ])

data_path = next(
    (path for path in possible_paths if path.exists()),
    None,
)

if data_path is None:
    raise FileNotFoundError(
        "Could not find prices.txt.\n"
        f"Current working directory: {Path.cwd()}"
    )

prices = pd.read_csv(
    data_path,
    sep=r"\s+",
    header=0,
)

prices = prices.apply(
    pd.to_numeric,
    errors="raise",
)

prices.index.name = "day"

print("=" * 70)
print("CROSS-ASSET PCA REGRESSION")
print("=" * 70)

print("\nLoaded from:")
print(data_path.resolve())

print("\nPrice data shape:")
print(prices.shape)

print("\nAssets:")
print(prices.columns.tolist())


# ============================================================
# VALIDATE DATA
# ============================================================

missing_values = prices.isna().sum().sum()
infinite_values = np.isinf(prices.to_numpy()).sum()

if missing_values > 0:
    raise ValueError(
        f"The price data contains {missing_values} missing values."
    )

if infinite_values > 0:
    raise ValueError(
        f"The price data contains {infinite_values} infinite values."
    )

if len(prices) <= TEST_DAYS:
    raise ValueError(
        "TEST_DAYS must be smaller than the number of price observations."
    )

print("\nMissing values:", missing_values)
print("Infinite values:", infinite_values)


# ============================================================
# CALCULATE RETURNS
# ============================================================

returns = (
    prices
    .pct_change()
    .replace([np.inf, -np.inf], np.nan)
    .dropna()
)

print("\nReturn data shape:")
print(returns.shape)


# ============================================================
# ALIGN CURRENT RETURNS WITH NEXT-DAY RETURNS
# ============================================================

# Predictor row:
# Returns observed on day t.
current_returns = returns.iloc[:-1].copy()

# Target row:
# Returns observed on day t + 1.
next_returns = returns.iloc[1:].copy()

# Re-index current returns using the target day.
# Therefore, a row indexed 800 contains:
# X = returns from day 799
# y = target asset return on day 800
current_returns.index = next_returns.index

if not current_returns.index.equals(next_returns.index):
    raise ValueError(
        "Predictor and target indices are not aligned."
    )

print("\nPredictor matrix shape:")
print(current_returns.shape)

print("Target matrix shape:")
print(next_returns.shape)


# ============================================================
# TRAIN/TEST SPLIT
# ============================================================

# With 1,000 price days and 200 test days, this gives day 800.
split_day = len(prices) - TEST_DAYS

training_mask = current_returns.index < split_day
testing_mask = current_returns.index >= split_day

print("\nSplit day:", split_day)
print(
    "Training samples:",
    int(training_mask.sum()),
)
print(
    "Testing samples:",
    int(testing_mask.sum()),
)

print(
    "Training target days:",
    current_returns.index[training_mask].min(),
    "to",
    current_returns.index[training_mask].max(),
)

print(
    "Testing target days:",
    current_returns.index[testing_mask].min(),
    "to",
    current_returns.index[testing_mask].max(),
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def evaluate_predictions(
    y_true,
    predictions,
):
    """
    Calculate out-of-sample forecasting metrics.
    """

    y_true = np.asarray(y_true)
    predictions = np.asarray(predictions)

    rmse = np.sqrt(
        mean_squared_error(
            y_true,
            predictions,
        )
    )

    mae = mean_absolute_error(
        y_true,
        predictions,
    )

    r_squared = r2_score(
        y_true,
        predictions,
    )

    directional_accuracy = np.mean(
        np.sign(predictions)
        ==
        np.sign(y_true)
    )

    if (
        np.std(predictions) == 0
        or np.std(y_true) == 0
    ):
        prediction_correlation = np.nan
    else:
        prediction_correlation = np.corrcoef(
            y_true,
            predictions,
        )[0, 1]

    return {
        "rmse": rmse,
        "mae": mae,
        "r_squared": r_squared,
        "directional_accuracy": directional_accuracy,
        "prediction_correlation": prediction_correlation,
    }


def evaluate_strategy(
    y_true,
    predictions,
    transaction_cost=0.0,
):
    """
    Create a basic long/short strategy:

    positive prediction -> long
    negative prediction -> short

    This is only an initial diagnostic.
    """

    y_true = np.asarray(y_true)
    predictions = np.asarray(predictions)

    positions = np.sign(predictions)

    # Position changes:
    # 0 to +1 gives turnover 1
    # +1 to -1 gives turnover 2
    turnover = np.abs(
        np.diff(
            np.concatenate([
                [0],
                positions,
            ])
        )
    )

    gross_returns = positions * y_true

    net_returns = (
        gross_returns
        - transaction_cost * turnover
    )

    cumulative_growth = np.cumprod(
        1 + net_returns
    )

    total_return = (
        cumulative_growth[-1] - 1
    )

    return_std = np.std(
        net_returns,
        ddof=1,
    )

    if return_std == 0:
        sharpe_ratio = np.nan
    else:
        sharpe_ratio = (
            np.sqrt(252)
            * np.mean(net_returns)
            / return_std
        )

    return {
        "strategy_total_return": total_return,
        "strategy_sharpe": sharpe_ratio,
        "average_turnover": np.mean(turnover),
    }


def run_asset_model(
    target_asset,
    feature_mode,
):
    """
    Fit and evaluate PCA regression for one target asset.

    feature_mode = "all_assets"
        Includes the target asset's current return.

    feature_mode = "other_assets_only"
        Removes the target asset from the predictors.
    """

    y = next_returns[target_asset].copy()

    if feature_mode == "all_assets":
        X = current_returns.copy()

    elif feature_mode == "other_assets_only":
        X = current_returns.drop(
            columns=[target_asset]
        )

    else:
        raise ValueError(
            f"Unknown feature mode: {feature_mode}"
        )

    X_train = X.loc[training_mask]
    X_test = X.loc[testing_mask]

    y_train = y.loc[training_mask]
    y_test = y.loc[testing_mask]

    number_of_features = X_train.shape[1]

    component_candidates = sorted(
        set(
            component
            for component in (
                COMPONENT_CANDIDATES
                + [number_of_features]
            )
            if component <= number_of_features
        )
    )

    # --------------------------------------------------------
    # PCA + LINEAR REGRESSION
    # --------------------------------------------------------

    pca_pipeline = Pipeline([
        (
            "scaler",
            StandardScaler(),
        ),
        (
            "pca",
            PCA(),
        ),
        (
            "regression",
            LinearRegression(),
        ),
    ])

    time_series_cv = TimeSeriesSplit(
        n_splits=CV_SPLITS
    )

    pca_search = GridSearchCV(
        estimator=pca_pipeline,
        param_grid={
            "pca__n_components":
                component_candidates
        },
        scoring="neg_mean_squared_error",
        cv=time_series_cv,
        n_jobs=-1,
        error_score="raise",
    )

    pca_search.fit(
        X_train,
        y_train,
    )

    best_pca_model = (
        pca_search.best_estimator_
    )

    pca_predictions = (
        best_pca_model.predict(X_test)
    )

    pca_metrics = evaluate_predictions(
        y_test,
        pca_predictions,
    )

    pca_strategy = evaluate_strategy(
        y_test,
        pca_predictions,
        transaction_cost=TRANSACTION_COST,
    )

    selected_components = (
        pca_search.best_params_[
            "pca__n_components"
        ]
    )

    explained_variance = (
        best_pca_model
        .named_steps["pca"]
        .explained_variance_ratio_
        .sum()
    )

    cross_validation_rmse = np.sqrt(
        -pca_search.best_score_
    )

    # --------------------------------------------------------
    # ZERO-RETURN BASELINE
    # --------------------------------------------------------

    zero_predictions = np.zeros(
        len(y_test)
    )

    zero_metrics = evaluate_predictions(
        y_test,
        zero_predictions,
    )

    # --------------------------------------------------------
    # PREVIOUS-RETURN BASELINE
    # --------------------------------------------------------

    previous_return_predictions = (
        current_returns
        .loc[testing_mask, target_asset]
        .to_numpy()
    )

    previous_metrics = evaluate_predictions(
        y_test,
        previous_return_predictions,
    )

    # --------------------------------------------------------
    # RIDGE REGRESSION WITHOUT PCA
    # --------------------------------------------------------

    ridge_model = Pipeline([
        (
            "scaler",
            StandardScaler(),
        ),
        (
            "ridge",
            Ridge(alpha=1.0),
        ),
    ])

    ridge_model.fit(
        X_train,
        y_train,
    )

    ridge_predictions = (
        ridge_model.predict(X_test)
    )

    ridge_metrics = evaluate_predictions(
        y_test,
        ridge_predictions,
    )

    # --------------------------------------------------------
    # RETURN RESULTS
    # --------------------------------------------------------

    return {
        "asset": target_asset,
        "feature_mode": feature_mode,

        "number_of_features":
            number_of_features,

        "selected_components":
            selected_components,

        "variance_explained":
            explained_variance,

        "cross_validation_rmse":
            cross_validation_rmse,

        "pca_rmse":
            pca_metrics["rmse"],

        "pca_mae":
            pca_metrics["mae"],

        "pca_r_squared":
            pca_metrics["r_squared"],

        "pca_directional_accuracy":
            pca_metrics[
                "directional_accuracy"
            ],

        "pca_prediction_correlation":
            pca_metrics[
                "prediction_correlation"
            ],

        "zero_rmse":
            zero_metrics["rmse"],

        "previous_return_rmse":
            previous_metrics["rmse"],

        "ridge_rmse":
            ridge_metrics["rmse"],

        "ridge_r_squared":
            ridge_metrics["r_squared"],

        "ridge_directional_accuracy":
            ridge_metrics[
                "directional_accuracy"
            ],

        "pca_beats_zero":
            pca_metrics["rmse"]
            < zero_metrics["rmse"],

        "pca_beats_previous_return":
            pca_metrics["rmse"]
            < previous_metrics["rmse"],

        "pca_beats_ridge":
            pca_metrics["rmse"]
            < ridge_metrics["rmse"],

        **pca_strategy,
    }


# ============================================================
# RUN EVERY ASSET
# ============================================================

target_assets = [
    asset
    for asset in prices.columns
    if asset not in EXCLUDED_TARGETS
]

feature_modes = [
    "all_assets",
    "other_assets_only",
]

results_list = []

total_models = (
    len(target_assets)
    * len(feature_modes)
)

model_number = 0

for feature_mode in feature_modes:

    print("\n" + "=" * 70)
    print("FEATURE MODE:", feature_mode)
    print("=" * 70)

    for target_asset in target_assets:

        model_number += 1

        print(
            f"[{model_number}/{total_models}] "
            f"Testing {target_asset}...",
            end=" ",
        )

        try:
            asset_result = run_asset_model(
                target_asset=target_asset,
                feature_mode=feature_mode,
            )

            results_list.append(
                asset_result
            )

            print(
                "done | "
                f"PCs={asset_result['selected_components']} | "
                f"R²={asset_result['pca_r_squared']:.4f} | "
                f"Direction="
                f"{asset_result['pca_directional_accuracy']:.3f}"
            )

        except Exception as error:
            print("FAILED")
            print(error)


results = pd.DataFrame(
    results_list
)


# ============================================================
# SAVE RESULTS
# ============================================================

output_path = (
    Path.cwd()
    / "pca_cross_asset_results.csv"
)

results.to_csv(
    output_path,
    index=False,
)

print("\nResults saved to:")
print(output_path.resolve())


# ============================================================
# PRINT SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("OVERALL RESULTS")
print("=" * 70)

for feature_mode in feature_modes:

    mode_results = results[
        results["feature_mode"]
        == feature_mode
    ].copy()

    number_tested = len(mode_results)

    positive_r_squared = (
        mode_results["pca_r_squared"] > 0
    ).sum()

    positive_correlation = (
        mode_results[
            "pca_prediction_correlation"
        ] > 0
    ).sum()

    direction_above_half = (
        mode_results[
            "pca_directional_accuracy"
        ] > 0.5
    ).sum()

    beats_zero = (
        mode_results["pca_beats_zero"]
    ).sum()

    beats_previous = (
        mode_results[
            "pca_beats_previous_return"
        ]
    ).sum()

    beats_ridge = (
        mode_results["pca_beats_ridge"]
    ).sum()

    print("\nFeature mode:", feature_mode)

    print(
        "Assets tested:",
        number_tested,
    )

    print(
        "Positive out-of-sample R²:",
        f"{positive_r_squared}/{number_tested}",
    )

    print(
        "Positive prediction correlation:",
        f"{positive_correlation}/{number_tested}",
    )

    print(
        "Directional accuracy above 50%:",
        f"{direction_above_half}/{number_tested}",
    )

    print(
        "PCA beats zero-return baseline:",
        f"{beats_zero}/{number_tested}",
    )

    print(
        "PCA beats previous-return baseline:",
        f"{beats_previous}/{number_tested}",
    )

    print(
        "PCA beats Ridge without PCA:",
        f"{beats_ridge}/{number_tested}",
    )

    print(
        "Median PCA R²:",
        mode_results[
            "pca_r_squared"
        ].median(),
    )

    print(
        "Median directional accuracy:",
        mode_results[
            "pca_directional_accuracy"
        ].median(),
    )

    print(
        "Median selected components:",
        mode_results[
            "selected_components"
        ].median(),
    )


# ============================================================
# DISPLAY BEST RESULTS
# ============================================================

columns_to_show = [
    "asset",
    "feature_mode",
    "selected_components",
    "variance_explained",
    "pca_r_squared",
    "pca_directional_accuracy",
    "pca_prediction_correlation",
    "pca_rmse",
    "zero_rmse",
    "ridge_rmse",
    "strategy_total_return",
    "strategy_sharpe",
]

best_results = (
    results
    .sort_values(
        "pca_r_squared",
        ascending=False,
    )
    [columns_to_show]
    .head(15)
)

print("\n" + "=" * 70)
print("TOP 15 RESULTS BY OUT-OF-SAMPLE R²")
print("=" * 70)

print(
    best_results.to_string(
        index=False
    )
)


# ============================================================
# PLOT OUT-OF-SAMPLE R² DISTRIBUTION
# ============================================================

plt.figure(figsize=(10, 5))

for feature_mode in feature_modes:

    mode_results = results[
        results["feature_mode"]
        == feature_mode
    ]

    plt.hist(
        mode_results["pca_r_squared"],
        bins=15,
        alpha=0.6,
        label=feature_mode,
    )

plt.axvline(
    0,
    linestyle="--",
    linewidth=1,
)

plt.xlabel("Out-of-sample R-squared")
plt.ylabel("Number of assets")
plt.title(
    "Cross-asset PCA regression performance"
)
plt.legend()
plt.grid(alpha=0.3)

plt.show()


# ============================================================
# PLOT TOP ASSETS
# ============================================================

top_plot_results = (
    results
    .sort_values(
        "pca_r_squared",
        ascending=False,
    )
    .head(15)
    .copy()
)

top_plot_results["label"] = (
    top_plot_results["asset"]
    + " | "
    + top_plot_results["feature_mode"]
)

plt.figure(figsize=(11, 6))

plt.barh(
    top_plot_results["label"],
    top_plot_results["pca_r_squared"],
)

plt.axvline(
    0,
    linestyle="--",
    linewidth=1,
)

plt.xlabel("Out-of-sample R-squared")
plt.ylabel("Asset and feature mode")
plt.title(
    "Best cross-asset PCA regression results"
)

plt.gca().invert_yaxis()
plt.grid(
    axis="x",
    alpha=0.3,
)
plt.tight_layout()

plt.show()