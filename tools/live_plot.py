#!/usr/bin/env python3
"""Живой график очереди A для интерактивного сценария.

Вызывается из C++ через system() раз в N модельных секунд. Показывает
мгновенную длину очереди A до текущего момента и историю параметра.
Окно закрывается пользователем, после чего C++ спрашивает новое значение.

Требования: matplotlib.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CSV = REPO / "results" / "2_tgreen_interactive" / "ramp_interval.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="live_plot.py",
        description="График очереди A до текущего модельного времени.",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        help="interval csv текущего прогона")
    parser.add_argument("--log", type=Path, default=None,
                        help="csv изменений параметра")
    parser.add_argument("--param", default="t_green",
                        help="имя изменяемого параметра")
    parser.add_argument("--value", type=float, default=float("nan"),
                        help="текущее значение параметра")
    parser.add_argument("--time", type=float, default=None,
                        help="текущее модельное время")
    parser.add_argument("--save", type=Path, default=None,
                        help="сохранить png вместо показа окна")
    parser.add_argument("--dpi", type=int, default=130, help="разрешение png")
    return parser


def read_interval(path: Path) -> tuple[list[float], list[float]]:
    times: list[float] = []
    queue: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"{path}: пустой файл")
        for row in reader:
            times.append(float(row["model_time"]))
            queue.append(float(row["queue_a"]))

    if not times:
        raise RuntimeError(f"{path}: ещё нет данных")
    return times, queue


def read_log(path: Path | None) -> tuple[list[float], list[float]]:
    if path is None or not path.exists():
        return [], []
    times: list[float] = []
    values: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            times.append(float(row["model_time"]))
            values.append(float(row["value"]))
    return times, values


def main() -> int:
    args = build_parser().parse_args()

    import matplotlib
    if args.save is not None:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        times, queue = read_interval(args.csv)
    except (OSError, RuntimeError) as error:
        print(f"live_plot: {error}")
        return 1

    log_t, log_v = read_log(args.log)

    fig, ax = plt.subplots(figsize=(10.5, 5.2), dpi=args.dpi)
    ax.plot(times, queue, color="#1f77b4", lw=1.4, alpha=0.90,
            label="мгновенная очередь A")
    ax.set_xlabel("модельное время, сек")
    ax.set_ylabel("длина очереди A, машин")
    ax.grid(alpha=0.3)
    ax.set_zorder(2)
    ax.patch.set_visible(False)
    handles, labels = ax.get_legend_handles_labels()

    if args.time is not None:
        ax.axvline(args.time, color="#d62728", ls="--", lw=1.2,
                   label=f"текущее время t={args.time:g}")

    if log_v:
        ax2 = ax.twinx()
        ax2.step(log_t, log_v, where="post", color="#ff7f0e", lw=1.6,
                 label=f"{args.param} (ступенька)")
        ax2.plot(log_t, log_v, "o", ms=3.0, color="#ff7f0e",
                 label="изменения параметра")
        ax2.set_ylabel(f"{args.param}, сек")
        ax2.grid(False)
        log_handles, log_labels = ax2.get_legend_handles_labels()
        handles += log_handles
        labels += log_labels

    value_text = "" if args.value != args.value else f", {args.param}={args.value:g}"
    time_text = "" if args.time is None else f", t={args.time:g}"
    ax.set_title(f"Очередь A до текущего момента{value_text}{time_text}")
    ax.legend(handles, labels, loc="upper left", fontsize=8, framealpha=0.85)
    x_max = float(times[-1])
    if args.time is not None:
        x_max = max(x_max, args.time)
    ax.set_xlim(0.0, x_max * 1.01 if x_max > 0 else 1.0)
    fig.tight_layout()

    if args.save is not None:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save)
        plt.close(fig)
        print(f"live_plot: сохранено {args.save}")
    else:
        # Блокирующий показ: C++ ждёт, пока пользователь закроет окно.
        plt.show()
        plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
