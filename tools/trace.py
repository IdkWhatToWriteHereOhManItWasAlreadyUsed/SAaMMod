from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TIME_ALIASES = ("modeltime", "time", "t", "модельноевремя", "время")
REPLICATION_ALIASES = ("replication", "run", "runnumber", "прогон", "репликация")

CSV_FIELDS = (
    "replication",
    "modelTime",
    "queue_a",
    "avg_queue_a",
    "queue_b",
    "avg_queue_b",
    "passed",
    "max_queue_a",
    "max_queue_b",
    "passage",
    "avg_passage",
    "wait",
    "avg_wait",
)

KNOWN_FIELDS = set(CSV_FIELDS)


@dataclass
class Run:
    source: str
    replication: str
    times: np.ndarray
    columns: dict[str, np.ndarray]

    @property
    def t_start(self) -> float:
        return float(self.times[0])

    @property
    def t_end(self) -> float:
        return float(self.times[-1])

    def has(self, name: str) -> bool:
        return name in self.columns and self.columns[name].size > 0

    def last(self, name: str) -> float | None:
        if not self.has(name):
            return None
        return float(self.columns[name][-1])


def normalize(name: str) -> str:
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    if key in TIME_ALIASES:
        return "modelTime"
    if key in REPLICATION_ALIASES:
        return "replication"
    return key


def split_runs(rows: list[dict], source: str) -> list[Run]:
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    has_replication = any(row.get("replication") not in (None, "") for row in rows)

    if has_replication:
        for row in rows:
            key = str(row.get("replication") or "")
            if key not in grouped:
                grouped[key] = []
                order.append(key)
            grouped[key].append(row)
    else:
        current = "1"
        grouped[current] = []
        order.append(current)
        previous = None
        for row in rows:
            time = row.get("modelTime")
            if previous is not None and time is not None and time < previous - 1e-12:
                current = str(len(order) + 1)
                grouped[current] = []
                order.append(current)
            grouped[current].append(row)
            previous = time if time is not None else previous

    runs: list[Run] = []
    for key in order:
        block = grouped[key]
        times = np.array([float(r["modelTime"]) for r in block if r.get("modelTime") not in (None, "")])
        if times.size == 0:
            continue
        order_idx = np.argsort(times, kind="stable")
        times = times[order_idx]

        columns: dict[str, np.ndarray] = {}
        for field in CSV_FIELDS:
            if field in ("modelTime", "replication"):
                continue
            values = [r.get(field) for r in block]
            if all(v in (None, "") for v in values):
                continue
            array = np.array([np.nan if v in (None, "") else float(v) for v in values])
            columns[field] = array[order_idx]

        runs.append(Run(source=source, replication=key, times=times, columns=columns))

    return runs


def read_csv(path: Path) -> tuple[list[Run], list[str]]:
    warnings: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], [f"{path.name}: пустой файл"]

        mapping = {normalize(name): name for name in reader.fieldnames if name}
        if "modelTime" not in mapping:
            return [], [f"{path.name}: нет колонки modelTime"]

        rows: list[dict] = []
        for raw in reader:
            row: dict = {}
            for canonical, original in mapping.items():
                value = raw.get(original)
                row[canonical] = value.strip() if isinstance(value, str) else value
            if row.get("modelTime") in (None, ""):
                continue
            try:
                row["modelTime"] = float(row["modelTime"])
            except (TypeError, ValueError):
                continue
            rows.append(row)

    unknown = sorted({normalize(n) for n in reader.fieldnames if n} - KNOWN_FIELDS)
    if unknown:
        warnings.append(f"{path.name}: проигнорированы неизвестные колонки {', '.join(unknown)}")

    runs = split_runs(rows, path.name)
    if not runs:
        return [], [f"{path.name}: не найдено ни одного прогона"]

    for run in runs:
        if run.t_start > 1e-9:
            warnings.append(f"{path.name}[{run.replication}]: первый отсчёт при t={run.t_start:.3f}, а не при t=0")
        if not run.has("passed"):
            warnings.append(f"{path.name}[{run.replication}]: нет колонки passed")
        if not (run.has("avg_queue_a") and run.has("queue_a")):
            warnings.append(f"{path.name}[{run.replication}]: нет колонок очереди A")
        if not (run.has("avg_queue_b") and run.has("queue_b")):
            warnings.append(f"{path.name}[{run.replication}]: нет колонок очереди B")
        if not (run.has("max_queue_a") and run.has("max_queue_b")):
            warnings.append(f"{path.name}[{run.replication}]: нет колонок максимума очереди")
        if not (run.has("avg_passage") and run.has("passage")):
            warnings.append(f"{path.name}[{run.replication}]: нет колонок времени прохождения")
        if not (run.has("avg_wait") and run.has("wait")):
            warnings.append(f"{path.name}[{run.replication}]: нет колонок времени ожидания в очереди")

    return runs, warnings


def hold_interp(grid: np.ndarray, times: np.ndarray, values: np.ndarray) -> np.ndarray:
    index = np.searchsorted(times, grid, side="right") - 1
    index = np.clip(index, 0, values.size - 1)
    return values[index]


def time_weighted_mean(times: np.ndarray, values: np.ndarray) -> np.ndarray:
    result = np.zeros_like(values, dtype=float)
    if times.size < 2:
        return result
    steps = np.diff(times)
    area = np.cumsum(values[:-1] * steps)
    with np.errstate(divide="ignore", invalid="ignore"):
        result[1:] = np.where(times[1:] > 0, area / times[1:], 0.0)
    return result


Event = tuple[float, str, str, str]


def _runs_from_events(events: list[Event], source: str) -> tuple[list[Run], list[str]]:
    warnings: list[str] = []
    blocks: list[list[Event]] = []
    current: list[Event] = []
    previous = None
    for event in events:
        if previous is not None and event[0] < previous - 1e-12:
            blocks.append(current)
            current = []
        current.append(event)
        previous = event[0]
    if current:
        blocks.append(current)
    if len(blocks) > 1:
        warnings.append(f"{source}: найдено прогонов в одном файле: {len(blocks)} (по сбросу времени)")

    runs: list[Run] = []
    for index, block in enumerate(blocks, start=1):
        times = np.array(sorted({0.0} | {e[0] for e in block}), dtype=float)

        columns: dict[str, np.ndarray] = {}
        for direction in ("a", "b"):
            letter = direction.upper()
            arrived = np.sort(np.array([e[0] for e in block if e[1] == "arrive" and e[2] == letter], dtype=float))
            entered = np.sort(np.array([e[0] for e in block if e[1] == "enter" and e[2] == letter], dtype=float))
            queue = np.searchsorted(arrived, times, side="right") - np.searchsorted(entered, times, side="right")
            columns[f"queue_{direction}"] = queue.astype(float)
            columns[f"avg_queue_{direction}"] = time_weighted_mean(times, queue.astype(float))
            columns[f"max_queue_{direction}"] = np.maximum.accumulate(queue).astype(float)

        left_times = np.sort(np.array([e[0] for e in block if e[1] == "leave"], dtype=float))
        columns["passed"] = np.searchsorted(left_times, times, side="right").astype(float)

        arrived_at: dict[str, float] = {}
        for time, action, _letter, car_id in block:
            if action == "arrive":
                arrived_at[car_id] = time
        departures = []
        lengths = []
        for time, action, _letter, car_id in block:
            if action == "leave" and car_id in arrived_at:
                departures.append(time)
                lengths.append(time - arrived_at[car_id])
        if departures:
            departures = np.array(departures, dtype=float)
            lengths = np.array(lengths, dtype=float)
            cumulated = np.cumsum(lengths)
            counts = np.arange(1, lengths.size + 1, dtype=float)
            last_index = np.searchsorted(departures, times, side="right") - 1
            safe = np.clip(last_index, 0, cumulated.size - 1)
            columns["avg_passage"] = np.where(last_index >= 0, cumulated[safe] / counts[safe], 0.0)
            columns["passage"] = np.where(last_index >= 0, lengths[safe], 0.0)
        else:
            columns["avg_passage"] = np.zeros_like(times)
            columns["passage"] = np.zeros_like(times)

        enters = []
        waits = []
        for time, action, _letter, car_id in block:
            if action == "enter" and car_id in arrived_at:
                enters.append(time)
                waits.append(time - arrived_at[car_id])
        if enters:
            enters = np.array(enters, dtype=float)
            waits = np.array(waits, dtype=float)
            cumulated = np.cumsum(waits)
            counts = np.arange(1, waits.size + 1, dtype=float)
            last_index = np.searchsorted(enters, times, side="right") - 1
            safe = np.clip(last_index, 0, cumulated.size - 1)
            columns["avg_wait"] = np.where(last_index >= 0, cumulated[safe] / counts[safe], 0.0)
            columns["wait"] = np.where(last_index >= 0, waits[safe], 0.0)
        else:
            columns["avg_wait"] = np.zeros_like(times)
            columns["wait"] = np.zeros_like(times)

        runs.append(Run(source=source, replication=str(index), times=times, columns=columns))

    if runs:
        warnings.append(f"{source}: t_end взят по времени последнего события, а не из stop() модели")
    return runs, warnings


def read_jsonl(path: Path) -> tuple[list[Run], list[str]]:
    events: list[Event] = []
    broken = 0
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                broken += 1
                continue
            time = float(record.get("time", 0.0))
            data = record.get("data") or {}
            sender = record.get("sender")
            if sender == "car":
                action = str(data.get("action", ""))
                if action:
                    direction = str(data.get("direction") or "A")[:1].upper()
                    events.append((time, action, direction, str(data.get("id", ""))))
            elif sender == "traffic_light":
                events.append((time, "light", str(data.get("to") or "N")[:1].upper(), ""))

    warnings: list[str] = []
    if broken:
        warnings.append(f"{path.name}: не разобрано строк: {broken}")
    if not events:
        return [], [f"{path.name}: нет событий"]

    events.sort(key=lambda e: e[0])
    return _runs_from_events(events, path.name)


def load(paths: list[Path]) -> tuple[list[Run], list[str]]:
    runs: list[Run] = []
    warnings: list[str] = []
    for path in paths:
        if not path.is_file():
            warnings.append(f"{path}: файл не найден")
            continue
        if path.suffix.lower() in (".csv", ".txt", ".tsv"):
            loaded, issues = read_csv(path)
        else:
            loaded, issues = read_jsonl(path)
        runs.extend(loaded)
        warnings.extend(issues)
    return runs, warnings
