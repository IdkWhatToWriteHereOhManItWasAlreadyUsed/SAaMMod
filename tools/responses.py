from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from trace import Run, hold_interp


@dataclass(frozen=True)
class Response:
    key: str
    title: str
    value: str
    mean: str | None
    ylabel: str
    color: str
    kind: str
    final_column: str
    step: bool = True


RESPONSES: tuple[Response, ...] = (
    Response(
        key="avg_queue_a",
        title="Средняя длина очереди со стороны A",
        value="queue_a",
        mean="avg_queue_a",
        ylabel="Длина очереди, машин",
        color="#1f77b4",
        kind="непрерывный",
        final_column="avg_queue_a",
        step=True,
    ),
    Response(
        key="avg_queue_b",
        title="Средняя длина очереди со стороны B",
        value="queue_b",
        mean="avg_queue_b",
        ylabel="Длина очереди, машин",
        color="#d62728",
        kind="непрерывный",
        final_column="avg_queue_b",
        step=True,
    ),
    Response(
        key="max_queue_a",
        title="Максимальная длина очереди со стороны A",
        value="max_queue_a",
        mean=None,
        ylabel="Длина очереди, машин",
        color="#1f77b4",
        kind="максимум",
        final_column="max_queue_a",
        step=True,
    ),
    Response(
        key="max_queue_b",
        title="Максимальная длина очереди со стороны B",
        value="max_queue_b",
        mean=None,
        ylabel="Длина очереди, машин",
        color="#d62728",
        kind="максимум",
        final_column="max_queue_b",
        step=True,
    ),
    Response(
        key="passed",
        title="Количество проехавших машин",
        value="passed",
        mean=None,
        ylabel="Машин",
        color="#2ca02c",
        kind="финальный",
        final_column="passed",
        step=True,
    ),
    Response(
        key="avg_passage",
        title="Среднее время прохождения участка",
        value="passage",
        mean="avg_passage",
        ylabel="Время прохождения",
        color="#9467bd",
        kind="дискретный",
        final_column="avg_passage",
        step=False,
    ),
)

TABLE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("run", "Прогон", "прогон"),
    ("time_of_run", "Время прогона", "время прогона"),
    ("passed", "Проехало машин", "проехавших машин"),
    ("avg_queue_a", "Средняя очередь A", "средняя длина очереди A"),
    ("avg_queue_b", "Средняя очередь B", "средняя длина очереди B"),
    ("max_queue_a", "Макс. очередь A", "максимальная длина очереди A"),
    ("max_queue_b", "Макс. очередь B", "максимальная длина очереди B"),
    ("avg_passage", "Среднее время прохождения", "среднее время прохождения участка"),
)

MAX_RESPONSE_ROWS = 30


def available(response: Response, runs: list[Run]) -> bool:
    if not runs:
        return False
    if any(run.has(response.value) for run in runs):
        return True
    if response.mean and any(run.has(response.mean) for run in runs):
        return True
    return any(run.has(response.final_column) for run in runs)


def final_value(run: Run, response: Response) -> float | None:
    return run.last(response.final_column)


def common_grid(runs: list[Run]) -> np.ndarray:
    horizon = min(run.t_end for run in runs)
    steps: list[np.ndarray] = [np.diff(run.times) for run in runs if run.times.size > 1]
    step = float(np.median(np.concatenate(steps))) if steps else 1.0
    step = max(step, 1e-6)
    count = int(np.clip(round(horizon / step), 64, 4000))
    return np.linspace(0.0, horizon, count)


def accumulated_mean(runs: list[Run], response: Response, grid: np.ndarray) -> np.ndarray:
    source = response.mean or response.value
    series = []
    for run in runs:
        if not run.has(source):
            continue
        values = run.columns[source]
        if values.size == 0 or not np.isfinite(values).any():
            continue
        series.append(hold_interp(grid, run.times, values))
    if not series:
        return np.full(grid.shape, np.nan)
    return np.nanmean(np.vstack(series), axis=0)


def final_values(runs: list[Run], response: Response) -> np.ndarray:
    collected = [final_value(run, response) for run in runs]
    return np.array([v for v in collected if v is not None and np.isfinite(v)], dtype=float)


def summary_rows(runs: list[Run]) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for index, run in enumerate(runs, start=1):
        row: dict[str, float | str] = {"run": index, "replication": run.replication, "time_of_run": run.t_end}
        for response in RESPONSES:
            value = final_value(run, response)
            row[response.key] = value if value is not None else float("nan")
        rows.append(row)
    return rows


def _format(value: float | str) -> str:
    if isinstance(value, str):
        return value
    if value is None or not np.isfinite(value):
        return ""
    return f"{value:.2f}"


def _cell(row: dict[str, float | str], field: str) -> str:
    value = row.get(field, "")
    if field == "replication":
        return str(value)
    if field == "run":
        return f"{int(value)}" if np.isfinite(value) else ""
    return _format(value)


def write_summary_csv(path: Path, rows: list[dict[str, float | str]]) -> None:
    fields = ["run", "replication"] + [column[0] for column in TABLE_COLUMNS[1:]]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for row in rows:
            writer.writerow([_cell(row, field) for field in fields])
        average = ["average", ""]
        for field in fields[2:]:
            average.append(_format(_mean(rows, field)))
        writer.writerow(average)


def _mean(rows: list[dict[str, float | str]], field: str) -> float:
    values = np.array([float(row[field]) for row in rows if np.isfinite(float(row[field]))], dtype=float)
    return float(values.mean()) if values.size else float("nan")


def write_summary_md(path: Path, rows: list[dict[str, float | str]], title: str) -> None:
    fields = ["run"] + [column[0] for column in TABLE_COLUMNS[1:]]
    lines = [f"# {title}", "", "| " + " | ".join(column[1] for column in TABLE_COLUMNS) + " |"]
    lines.append("| " + " | ".join("---" for _ in TABLE_COLUMNS) + " |")

    if len(rows) <= MAX_RESPONSE_ROWS:
        for row in rows:
            lines.append("| " + " | ".join(_format(row.get(field, "")) for field in fields) + " |")
    else:
        lines.append(f"| … | | | | | | | | ({len(rows)} прогонов, полностью — в {path.stem}.csv) |")

    average: list[str] = ["**average**"]
    for field in fields[1:]:
        value = _mean(rows, field)
        average.append(f"**{_format(value)}**" if np.isfinite(value) else "")
    lines.append("| " + " | ".join(average) + " |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def text_summary(runs: list[Run]) -> list[str]:
    names = [response.title for response in RESPONSES] + ["Время прогона"]
    width = max(24, max(len(name) for name in names) + 2)
    lines = [f"прогонов: {len(runs)}"]
    header = f"{'отклик':<{width}}{'среднее':>12}{'мин':>12}{'макс':>12}{'ст.откл':>12}"
    lines.append(header)
    lines.append("-" * len(header))
    for response in RESPONSES:
        values = final_values(runs, response)
        if values.size == 0:
            continue
        deviation = values.std(ddof=1) if values.size > 1 else 0.0
        lines.append(f"{response.title:<{width}}{values.mean():>12.3f}{values.min():>12.3f}{values.max():>12.3f}{deviation:>12.3f}")
    times = np.array([run.t_end for run in runs], dtype=float)
    deviation = times.std(ddof=1) if times.size > 1 else 0.0
    lines.append(f"{'Время прогона':<{width}}{times.mean():>12.3f}{times.min():>12.3f}{times.max():>12.3f}{deviation:>12.3f}")
    return lines
