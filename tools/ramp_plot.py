#!/usr/bin/env python3
"""График средней взвешенной длины очереди со стороны A.

Читает результаты пункта 2:
    results/2_tgreen_interactive/ramp_interval.csv
    results/2_tgreen_interactive/ramp_log.csv

На левой оси — мгновенная длина очереди A, на правой — ступенчатый
график t_green в моменты изменения параметра.

Требования: numpy, matplotlib.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS = REPO / "results" / "2_tgreen_interactive"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ramp_plot.py",
        description="Очередь A и t_green во времени для сценария ramp.",
    )
    parser.add_argument(
        "--results", type=Path, default=DEFAULT_RESULTS,
        help=f"папка с результатами (по умолчанию {DEFAULT_RESULTS})",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="папка для графика (по умолчанию совпадает с --results)",
    )
    parser.add_argument("--dpi", type=int, default=150, help="разрешение png")
    return parser


def read_interval(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    times: list[float] = []
    queue: list[float] = []
    avg_queue: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"{path}: пустой файл")
        has_avg = "avg_queue_a" in reader.fieldnames
        for row in reader:
            times.append(float(row["model_time"]))
            queue.append(float(row["queue_a"]))
            if has_avg:
                avg_queue.append(float(row["avg_queue_a"]))

    t = np.array(times, dtype=float)
    q = np.array(queue, dtype=float)
    if not has_avg:
        # запасной вариант: средняя, взвешенная по шагам между отсчётами
        avg = np.zeros_like(q)
        for i in range(1, q.size):
            dt = t[i] - t[i - 1]
            avg[i] = (avg[i - 1] * t[i - 1] + q[i - 1] * dt) / t[i]
        return t, q, avg
    return t, q, np.array(avg_queue, dtype=float)


def read_ramp(path: Path) -> tuple[np.ndarray, np.ndarray]:
    times: list[float] = []
    values: list[float] = []
    if not path.exists():
        return np.array([]), np.array([])
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            times.append(float(row["model_time"]))
            values.append(float(row["value"]))
    return np.array(times, dtype=float), np.array(values, dtype=float)


def main() -> int:
    args = build_parser().parse_args()
    results = args.results
    out = args.out or results

    interval_path = results / "ramp_interval.csv"
    if not interval_path.exists():
        raise FileNotFoundError(f"нет файла: {interval_path}")
    t, queue, avg_queue = read_interval(interval_path)
    ramp_t, ramp_v = read_ramp(results / "ramp_log.csv")

    fig, ax = plt.subplots(figsize=(11.5, 5.8), dpi=args.dpi)
    ax.plot(t, queue, color="#1f77b4", lw=1.4, alpha=0.90,
            label="мгновенная очередь A")
    ax.set_xlabel("модельное время, сек")
    ax.set_ylabel("длина очереди A, машин")
    ax.grid(alpha=0.3)
    ax.set_zorder(2)
    ax.patch.set_visible(False)

    handles, labels = ax.get_legend_handles_labels()

    if ramp_v.size:
        ax2 = ax.twinx()
        ax2.step(ramp_t, ramp_v, where="post", color="#ff7f0e", lw=1.6,
                 label="t_green (ступенька)")
        ax2.plot(ramp_t, ramp_v, "o", ms=3.0, color="#ff7f0e",
                 label="моменты изменения t_green")
        ax2.set_ylabel("t_green, сек")
        ax2.grid(False)

        ramp_handles, ramp_labels = ax2.get_legend_handles_labels()
        handles += ramp_handles
        labels += ramp_labels

        step = float(ramp_v[1] - ramp_v[0]) if ramp_v.size > 1 else 0.0
        every = float(ramp_t[1] - ramp_t[0]) if ramp_v.size > 1 else 0.0
        schedule = (f"t_green: {ramp_v[0]:g} → {ramp_v[-1]:g} "
                    f"(+{step:g} каждые {every:g} с)")
        print(f"записей t_green: {ramp_v.size} "
              f"(начальное значение + изменения)")
        print(schedule)
        print(f"начальная средняя очередь A: {avg_queue[0]:.3f}")
        print(f"конечная средняя очередь A: {avg_queue[-1]:.3f}")
        print(f"максимум средней очереди A: {avg_queue.max():.3f}")
    else:
        schedule = "журнал изменений параметра не найден"
        print(schedule)

    ax.set_title("Пункт 2: мгновенная очередь A и t_green")
    ax.legend(handles, labels, loc="upper left", fontsize=8, framealpha=0.85)
    ax.set_xlim(0.0, float(t[-1]))

    fig.tight_layout()
    out.mkdir(parents=True, exist_ok=True)
    path = out / "queue_a_static.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"график: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
