import importlib.util
from pathlib import Path


def load_strategy(strategy_path: str, function_name: str = "getMyPosition"):
    path = Path(strategy_path)

    if not path.exists():
        raise FileNotFoundError(f"Strategy file not found: {strategy_path}")

    spec = importlib.util.spec_from_file_location("user_strategy", strategy_path)

    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import strategy file: {strategy_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, function_name):
        raise AttributeError(
            f"Strategy file must define {function_name}(prices)."
        )

    strategy_function = getattr(module, function_name)

    if not callable(strategy_function):
        raise TypeError(f"Strategy attribute {function_name} is not callable.")

    return strategy_function
