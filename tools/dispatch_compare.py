#!/usr/bin/env python3
"""Сравнение политик диспетчеризации светофора.

Читает results/3_dispatch/<case>/{fixed,clearance,adaptive}_summary.csv,
считает средние с 95% доверительными интервалами, парные t-тесты
относительно fixed и строит сводные графики.

Требования: numpy, scipy, matplotlib.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np
from scipy import stats

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS = REPO / "results" / "3_dispatch"

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dispatch_compare.py",
        description="Сравнение fixed / clearance / adaptive.",
    )
    parser.add_argument(
        "--case", choices=("symmetric", "asymmetric", "all"), default="all",
        help="набор нагрузки (по умолчанию all)",
    )
    parser.add_argument(
        "--results", type=Path, default=DEFAULT_RESULTS,
        help=f"папка результатов (по умолчанию {DEFAULT_RESULTS})",
    )
    parser.add_argument("--dpi", type=int, default=150, help="разрешение png")
    return parser


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

    def bars(ax, metric: str, title: str, ylabel: str,
             policies: tuple[str, ...] = POLICIES) -> None:
        means = []
        errors = []
        for policy in policies:
            mean, lo, hi = mean_ci(summary[metric][policy])
            means.append(mean)
            errors.append(hi - mean)
        positions = np.arange(len(policies))
        colors = [POLICY_COLORS[p] for p in policies]
        ax.bar(positions, means, yerr=errors, capsize=5,
               color=colors, alpha=0.85)
        for x, value in zip(positions, means):
            ax.text(x, value, f"{value:.2f}", ha="center", va="bottom",
                    fontsize=8)
        ax.set_xticks(positions)
        ax.set_xticklabels([POLICY_TITLES[p] for p in policies])
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3, axis="y")
        ax.set_axisbelow(True)

    bars(ax_y, "Y", f"{case}: среднее ожидание", "сек")
    bars(ax_passed, "passed", f"{case}: пропускная способность", "машин")

    width = 0.36
    positions = np.arange(len(POLICIES))
    for index, (metric, label, color) in enumerate((
        ("Y_a", "A", "#1f77b4"),
        ("Y_b", "B", "#d62728"),
    )):
        means = [mean_ci(summary[metric][p])[0] for p in POLICIES]
        errors = [mean_ci(summary[metric][p])[2] -
                  mean_ci(summary[metric][p])[0] for p in POLICIES]
        ax_dir.bar(positions + (index - 0.5) * width, means, width,
                   yerr=errors, capsize=4, color=color, alpha=0.85,
                   label=f"направление {label}")
    ax_dir.set_xticks(positions)
    ax_dir.set_xticklabels([POLICY_TITLES[p] for p in POLICIES])
    ax_dir.set_title(f"{case}: ожидание по направлениям")
    ax_dir.set_ylabel("сек")
    ax_dir.legend(fontsize=8)
    ax_dir.grid(alpha=0.3, axis="y")
    ax_dir.set_axisbelow(True)

    for index, (metric, label, color) in enumerate((
        ("avg_queue_a", "A", "#1f77b4"),
        ("avg_queue_b", "B", "#d62728"),
    )):
        means = [mean_ci(summary[metric][p])[0] for p in POLICIES]
        errors = [mean_ci(summary[metric][p])[2] -
                  mean_ci(summary[metric][p])[0] for p in POLICIES]
        ax_queue.bar(positions + (index - 0.5) * width, means, width,
                     yerr=errors, capsize=4, color=color, alpha=0.85,
                     label=f"направление {label}")
    ax_queue.set_xticks(positions)
    ax_queue.set_xticklabels([POLICY_TITLES[p] for p in POLICIES])
    ax_queue.set_title(f"{case}: средняя очередь")
    ax_queue.set_ylabel("машин")
    ax_queue.legend(fontsize=8)
    ax_queue.grid(alpha=0.3, axis="y")
    ax_queue.set_axisbelow(True)

    fig.suptitle("Сравнение политик диспетчеризации", fontsize=14)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    args = build_parser().parse_args()
    cases = ("symmetric", "asymmetric") if args.case == "all" else (args.case,)

    for case in cases:
        data = load_case(args.results, case)
        compare(data, case, args.results / case, args.dpi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
