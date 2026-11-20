#!/usr/bin/env python3
"""Сравнение политик диспетчеризации светофора.

Запускается без аргументов. Читает
results/3_dispatch/<case>/{fixed,clearance,adaptive}_summary.csv,
считает средние с 95% доверительными интервалами, парные t-тесты
относительно fixed и строит сводные графики для всех режимов
и обоих наборов нагрузки.

Требования: numpy, scipy, matplotlib.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from scipy import stats

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results" / "3_dispatch"
CASES = ("symmetric", "asymmetric")
DPI = 150

POLICIES = ("fixed", "clearance", "adaptive")
POLICY_TITLES = {
    "fixed": "fixed",
    "clearance": "clearance",
    "adaptive": "adaptive",
}
POLICY_COLORS = {
    "fixed": "#7f7f7f",
    "clearance": "#1f77b4",
    "adaptive": "#ff7f0e",
}

METRICS = (
    ("Y", "Среднее ожидание, сек"),
    ("Y_a", "Ожидание A, сек"),
    ("Y_b", "Ожидание B, сек"),
    ("passed", "Проехало машин"),
    ("avg_queue_a", "Средняя очередь A"),
    ("avg_queue_b", "Средняя очередь B"),
    ("max_queue_a", "Макс. очередь A"),
    ("max_queue_b", "Макс. очередь B"),
)


def read_summary(path: Path) -> dict[str, dict[str, float]]:
    """seed -> строка summary для одной политики."""
    rows: dict[str, dict[str, float]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            seed = str(row["seed"])
            rows[seed] = {key: float(value) for key, value in row.items()}
    return rows


def load_case(results: Path, case: str) -> dict[str, dict[str, float]]:
    data: dict[str, dict[str, float]] = {}
    for policy in POLICIES:
        path = results / case / f"{policy}_summary.csv"
        if not path.exists():
            raise FileNotFoundError(f"нет файла: {path}")
        data[policy] = read_summary(path)
    return data


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    n = int(values.size)
    mean = float(values.mean())
    if n < 2:
        return mean, mean, mean
    sd = float(values.std(ddof=1))
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n))
    return mean, mean - half, mean + half


def metric_values(rows: dict[str, dict[str, float]],
                  metric: str) -> tuple[np.ndarray, np.ndarray]:
    seeds = sorted(set(rows))
    values = np.array([rows[seed][metric] for seed in seeds], dtype=float)
    return np.array(seeds), values


def compare(data: dict[str, dict[str, float]], case: str,
            out_dir: Path, dpi: int) -> None:
    stats_rows: list[dict[str, object]] = []
    test_rows: list[dict[str, object]] = []
    summary: dict[str, dict[str, np.ndarray]] = {}

    print(f"\n=== {case} ===")
    header = (f"{'метрика':<22}" +
              "".join(f"{policy:>14}" for policy in POLICIES))
    print(header)
    print("-" * len(header))

    for metric, title in METRICS:
        values = {}
        for policy in POLICIES:
            seeds, vals = metric_values(data[policy], metric)
            values[policy] = (seeds, vals)
            mean, lo, hi = mean_ci(vals)
            stats_rows.append({
                "case": case,
                "policy": policy,
                "metric": metric,
                "mean": mean,
                "ci_low": lo,
                "ci_high": hi,
                "n": int(vals.size),
            })
        summary[metric] = {
            policy: values[policy][1] for policy in POLICIES
        }

        line = f"{metric:<22}"
        for policy in POLICIES:
            mean, lo, hi = mean_ci(values[policy][1])
            line += f"{mean:9.2f} ±{hi - mean:4.2f}"
        print(line)

    # Парные тесты: одинаковые seed'ы у всех политик.
    for metric, _title in METRICS:
        fixed_seeds, fixed_values = metric_values(data["fixed"], metric)
        fixed_map = dict(zip((str(s) for s in fixed_seeds), fixed_values))
        for policy in ("clearance", "adaptive"):
            other_seeds, other_values = metric_values(data[policy], metric)
            other_map = dict(zip((str(s) for s in other_seeds), other_values))
            common = sorted(set(fixed_map) & set(other_map))
            a = np.array([fixed_map[s] for s in common], dtype=float)
            b = np.array([other_map[s] for s in common], dtype=float)
            t_value, p_value = stats.ttest_rel(a, b)
            test_rows.append({
                "case": case,
                "metric": metric,
                "comparison": f"fixed vs {policy}",
                "mean_fixed": float(a.mean()),
                "mean_other": float(b.mean()),
                "t": float(t_value),
                "p": float(p_value),
            })

    print("\nпарные t-тесты (fixed — база):")
    for row in test_rows:
        marker = "*" if row["p"] < 0.05 else " "
        print(f"  {row['metric']:<14} fixed vs {row['comparison'].split(' vs ')[1]:<10} "
              f"Δ={row['mean_other'] - row['mean_fixed']:+8.2f}  "
              f"p={row['p']:.4f}{marker}")

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "dispatch_summary.csv"
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case", "policy", "metric", "mean", "ci_low", "ci_high", "n",
        ])
        writer.writeheader()
        writer.writerows(stats_rows)

    tests_path = out_dir / "dispatch_tests.csv"
    with tests_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case", "metric", "comparison", "mean_fixed", "mean_other",
            "t", "p",
        ])
        writer.writeheader()
        writer.writerows(test_rows)

    plot_case(case, summary, out_dir / "dispatch_comparison.png", dpi)
    print(f"сводка: {summary_path}")
    print(f"тесты: {tests_path}")
    print(f"график: {out_dir / 'dispatch_comparison.png'}")


def plot_case(case: str, summary: dict[str, dict[str, np.ndarray]],
              path: Path, dpi: int) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0), dpi=dpi)
    ax_y, ax_passed, ax_dir, ax_queue = axes.flat

    # Верхняя граница шкалы считается только по альтернативам; fixed
    # может выходить за неё, чтобы adaptive/clearance были видны крупно.
    def policy_top(metrics: tuple[str, ...],
                   policies: tuple[str, ...] = ("clearance", "adaptive")) -> float:
        return max(
            mean_ci(summary[metric][policy])[2]
            for metric in metrics
            for policy in policies
        )

    def add_labels(ax, positions, values, fmt: str = "{:.2f}") -> None:
        top = ax.get_ylim()[1]
        for x, value in zip(positions, values):
            if value > top * 0.98:
                ax.text(x, top * 0.97, fmt.format(value) + " ↑",
                        ha="center", va="top", fontsize=7)
            else:
                ax.text(x, value, fmt.format(value),
                        ha="center", va="bottom", fontsize=7)

    def bars(ax, metric: str, title: str, ylabel: str,
             limit: float | None = None) -> None:
        means = []
        errors = []
        for policy in POLICIES:
            mean, _lo, hi = mean_ci(summary[metric][policy])
            means.append(mean)
            errors.append(hi - mean)
        positions = np.arange(len(POLICIES))
        colors = [POLICY_COLORS[p] for p in POLICIES]
        ax.bar(positions, means, yerr=errors, capsize=5,
               color=colors, alpha=0.85)
        ax.set_xticks(positions)
        ax.set_xticklabels([POLICY_TITLES[p] for p in POLICIES])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3, axis="y")
        ax.set_axisbelow(True)
        if limit is not None:
            ax.set_ylim(0.0, limit)
        add_labels(ax, positions, means)

    y_limit = policy_top(("Y",)) * 1.15
    bars(ax_y, "Y",
         f"{case}: среднее ожидание (шкала по clearance/adaptive)",
         "сек", y_limit)

    # Пропускная способность: значения близки, ограничивать не нужно.
    bars(ax_passed, "passed", f"{case}: пропускная способность", "машин")

    width = 0.36
    positions = np.arange(len(POLICIES))
    dir_limit = policy_top(("Y_a", "Y_b")) * 1.15
    ax_dir.set_ylim(0.0, dir_limit)
    for index, (metric, label, color) in enumerate((
        ("Y_a", "A", "#1f77b4"),
        ("Y_b", "B", "#d62728"),
    )):
        means = [mean_ci(summary[metric][p])[0] for p in POLICIES]
        errors = [mean_ci(summary[metric][p])[2] -
                  mean_ci(summary[metric][p])[0] for p in POLICIES]
        offset = (index - 0.5) * width
        ax_dir.bar(positions + offset, means, width,
                   yerr=errors, capsize=4, color=color, alpha=0.85,
                   label=f"направление {label}")
        add_labels(ax_dir, positions + offset, means)
    ax_dir.set_xticks(positions)
    ax_dir.set_xticklabels([POLICY_TITLES[p] for p in POLICIES])
    ax_dir.set_title(f"{case}: ожидание по направлениям "
                     f"(шкала по clearance/adaptive)")
    ax_dir.set_ylabel("сек")
    ax_dir.legend(fontsize=8)
    ax_dir.grid(alpha=0.3, axis="y")
    ax_dir.set_axisbelow(True)

    queue_limit = policy_top(("avg_queue_a", "avg_queue_b")) * 1.15
    ax_queue.set_ylim(0.0, queue_limit)
    for index, (metric, label, color) in enumerate((
        ("avg_queue_a", "A", "#1f77b4"),
        ("avg_queue_b", "B", "#d62728"),
    )):
        means = [mean_ci(summary[metric][p])[0] for p in POLICIES]
        errors = [mean_ci(summary[metric][p])[2] -
                  mean_ci(summary[metric][p])[0] for p in POLICIES]
        offset = (index - 0.5) * width
        ax_queue.bar(positions + offset, means, width,
                     yerr=errors, capsize=4, color=color, alpha=0.85,
                     label=f"направление {label}")
        add_labels(ax_queue, positions + offset, means)
    ax_queue.set_xticks(positions)
    ax_queue.set_xticklabels([POLICY_TITLES[p] for p in POLICIES])
    ax_queue.set_title(f"{case}: средняя очередь "
                       f"(шкала по clearance/adaptive)")
    ax_queue.set_ylabel("машин")
    ax_queue.legend(fontsize=8)
    ax_queue.grid(alpha=0.3, axis="y")
    ax_queue.set_axisbelow(True)

    fig.suptitle("Сравнение политик диспетчеризации", fontsize=14)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    # Скрипт запускается без аргументов: всегда строит графики для всех
    # наборов нагрузки и всех политик.
    for case in CASES:
        data = load_case(RESULTS, case)
        compare(data, case, RESULTS / case, DPI)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
