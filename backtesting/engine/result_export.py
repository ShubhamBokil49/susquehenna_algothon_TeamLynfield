import csv
import json
from pathlib import Path
import secrets
from typing import Any, Iterable


def flatten_result_rows(
    results: dict[str, Any],
) -> Iterable[tuple[str, str, str, str]]:
    """Yield every result leaf in a lossless, long-form CSV representation."""
    for section, value in results.items():
        yield from _flatten_value(section, "$", value)


def _flatten_value(
    section: str,
    path: str,
    value: Any,
) -> Iterable[tuple[str, str, str, str]]:
    if isinstance(value, dict):
        if not value:
            yield section, path, "object", "{}"
            return

        for key, nested_value in value.items():
            yield from _flatten_value(
                section,
                f"{path}.{key}",
                nested_value,
            )
        return

    if isinstance(value, list):
        if not value:
            yield section, path, "array", "[]"
            return

        for index, nested_value in enumerate(value):
            yield from _flatten_value(
                section,
                f"{path}[{index}]",
                nested_value,
            )
        return

    if value is None:
        value_type = "null"
    elif isinstance(value, bool):
        value_type = "boolean"
    elif isinstance(value, int):
        value_type = "integer"
    elif isinstance(value, float):
        value_type = "number"
    else:
        value_type = "string"

    yield section, path, value_type, json.dumps(value, ensure_ascii=False)


def write_results_csv(results: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(
        f".{output_path.name}.{secrets.token_hex(4)}.tmp"
    )

    try:
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["section", "path", "value_type", "value_json"])
            writer.writerows(flatten_result_rows(results))
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path

