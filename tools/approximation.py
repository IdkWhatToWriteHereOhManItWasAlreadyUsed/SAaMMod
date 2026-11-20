#!/usr/bin/env python3
"""Аппроксимация зависимости отклика Y от t_green.

Читает результаты последовательного прогона src/main.cpp:
    results/1_tgreen/meta.csv
    results/1_tgreen/tgreen_x{k}_summary.csv

Для каждого уровня t_green считаются среднее Y, стандартное отклонение,
стандартная ошибка и 95% доверительный интервал. Затем по средним уровня
строятся полиномиальные аппроксимации 1, 2 и 3 степени:
    Y = c0 + c1*u + c2*u^2 + c3*u^3,   u = t_green - x0.

Лучшая модель выбирается по F-тесту добавленного члена (alpha = 0.05)
и adjusted R^2; AICc выводится как вспомогательный критерий.

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
DEFAULT_RESULTS = REPO / "results" / "1_tgreen"
ALPHA = 0.05
MODEL_NAMES = {1: "линейная", 2: "квадратичная", 3: "кубическая"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="approximation.py",
        description="Полиномиальная аппроксимация отклика Y от t_green.",
    )
    parser.add_argument(
        "--results", type=Path, default=DEFAULT_RESULTS,
        help=f"папка с результатами (по умолчанию {DEFAULT_RESULTS})",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="папка для графиков и сводки (по умолчанию совпадает с --results)",
    )
    parser.add_argument("--dpi", type=int, default=150, help="разрешение png")
    return parser


def read_meta(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        row = next(reader, None)
    if row is None:
        raise RuntimeError(f"{path}: пустой meta.csv")
    return row


def read_y(path: Path) -> np.ndarray:
    values: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            values.append(float(row["Y"]))
    if not values:
        raise RuntimeError(f"{path}: нет значений Y")
    return np.array(values, dtype=float)


def fit_polynomial(u: np.ndarray, y: np.ndarray, degree: int) -> dict:
    """МНК-полином по центрированной переменной u (OLS, степени 1..3)."""
    coeffs_desc = np.polyfit(u, y, degree)
    pred = np.polyval(coeffs_desc, u)
    residuals = y - pred
    rss = float(np.sum(residuals ** 2))
    tss = float(np.sum((y - y.mean()) ** 2))
    n = int(u.size)
    p = degree + 1

    r2 = 1.0 - rss / tss if tss > 0 else 1.0
    adj = 1.0 - (1.0 - r2) * (n - 1) / (n - p) if n > p else float("nan")
    rmse = math.sqrt(rss / n)
    if rss > 0 and n > p + 1:
        aicc = n * math.log(rss / n) + 2 * p + 2 * p * (p + 1) / (n - p - 1)
    else:
        aicc = float("inf")

    return {
        "degree": degree,
        "name": MODEL_NAMES[degree],
        "c": coeffs_desc[::-1].copy(),  # c[0] + c[1]*u + ...
        "pred": pred,
        "residuals": residuals,
        "rss": rss,
        "tss": tss,
        "r2": r2,
        "adj": adj,
        "rmse": rmse,
        "aicc": aicc,
        "p": p,
        "n": n,
        "f": float("nan"),
        "p_value": float("nan"),
    }


def nested_f(small: dict, big: dict) -> tuple[float, float]:
    """F-тест вложенных полиномов: проверяет вклад добавленных членов."""
    df1 = big["p"] - small["p"]
    df2 = big["n"] - big["p"]
    if df1 <= 0 or df2 <= 0:
        return float("nan"), float("nan")
    if big["rss"] <= 0:
        return float("nan"), float("nan")
    if small["rss"] <= big["rss"]:
        return 0.0, 1.0
    f_value = ((small["rss"] - big["rss"]) / df1) / (big["rss"] / df2)
    return f_value, float(stats.f.sf(f_value, df1, df2))


def equation(fit: dict, x0: float) -> str:
    """Уравнение вида Y = c0 + c1*u + c2*u^2 + ..."""
    c = fit["c"]
    parts = [f"{c[0]:.6g}"]
    for power in range(1, fit["degree"] + 1):
        value = float(c[power])
        sign = "+" if value >= 0 else "-"
        if power == 1:
            term = f"u"
        elif power == 2:
            term = "u²"
        else:
            term = "u³"
        parts.append(f" {sign} {abs(value):.6g}·{term}")
    return "Y = " + "".join(parts) + f",  u = t_green - {x0:.6g}"


def level_table(meta: dict, results: Path) -> tuple[np.ndarray, list[dict]]:
    x0 = float(meta["x0"])
    delta = float(meta["delta"])
    k_min = int(meta["k_min"])
    k_max = int(meta["k_max"])
    expected = int(meta.get("reps_per_level") or 0)

    xs: list[float] = []
    rows: list[dict] = []
    for k in range(k_min, k_max + 1):
        path = results / f"tgreen_x{k}_summary.csv"
        if not path.exists():
            raise FileNotFoundError(f"нет файла результатов: {path}")
        ys = read_y(path)
        if expected and ys.size != expected:
            print(f"предупреждение: {path.name}: реплик {ys.size}, "
                  f"ожидалось {expected}")
        n = int(ys.size)
        mean = float(ys.mean())
        s = float(ys.std(ddof=1)) if n > 1 else 0.0
        se = s / math.sqrt(n) if n > 0 else float("nan")
        t_cr = float(stats.t.ppf(0.975, n - 1)) if n > 1 else float("nan")
        half = t_cr * se if n > 1 else float("nan")

        x = x0 + k * delta
        xs.append(x)
        rows.append({
            "k": k, "x": x, "n": n, "values": ys,
            "mean": mean, "s": s, "se": se,
            "ci_lo": mean - half, "ci_hi": mean + half, "half": half,
        })
    return np.array(xs, dtype=float), rows


def select_best(fits: list[dict]) -> dict:
    """Иерархический выбор: степень растёт только при значимом F-тесте
    и росте adjusted R^2."""
    chosen = fits[0]
    for i in range(1, len(fits)):
        f_value, p_value = nested_f(fits[i - 1], fits[i])
        fits[i]["f"] = f_value
        fits[i]["p_value"] = p_value
        if p_value < ALPHA and fits[i]["adj"] > chosen["adj"]:
            chosen = fits[i]
    return chosen


def print_levels(rows: list[dict]) -> None:
    print("\n=== Уровни t_green и отклик Y ===")
    header = (f"{'k':>3} {'t_green':>10} {'n':>4} {'Y_mean':>10} "
              f"{'s':>9} {'95% ДИ':>22}")
    print(header)
    print("-" * len(header))
    for row in rows:
        ci = f"[{row['ci_lo']:.3f}; {row['ci_hi']:.3f}]"
        print(f"{row['k']:3d} {row['x']:10.3f} {row['n']:4d} "
              f"{row['mean']:10.4f} {row['s']:9.4f} {ci:>22}")


def print_fits(fits: list[dict], chosen: dict) -> None:
    print("\n=== Полиномиальные аппроксимации (u = t_green - x0) ===")
    header = (f"{'модель':<14}{'R²':>9}{'adj R²':>9}{'RMSE':>9}"
              f"{'AICc':>10}{'F':>9}{'p(F)':>9}  выбор")
    print(header)
    print("-" * len(header))
    for fit in fits:
        f_text = "" if math.isnan(fit["f"]) else f"{fit['f']:.3f}"
        p_text = "" if math.isnan(fit["p_value"]) else f"{fit['p_value']:.4f}"
        mark = "<-- лучшая" if fit is chosen else ""
        print(f"{fit['name']:<14}{fit['r2']:9.5f}{fit['adj']:9.5f}"
              f"{fit['rmse']:9.4f}{fit['aicc']:10.2f}"
              f"{f_text:>9}{p_text:>9}  {mark}")


def write_summary(path: Path, meta: dict, fits: list[dict],
                  chosen: dict) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "degree", "model", "c0", "c1", "c2", "c3",
            "r2", "adj_r2", "rmse", "aicc",
            "f_vs_prev", "p_vs_prev", "chosen",
        ])
        for fit in fits:
            c = fit["c"]
            coeffs = [c[i] if i < c.size else "" for i in range(4)]
            writer.writerow([
                fit["degree"], fit["name"], *coeffs,
                fit["r2"], fit["adj"], fit["rmse"], fit["aicc"],
                "" if math.isnan(fit["f"]) else fit["f"],
                "" if math.isnan(fit["p_value"]) else fit["p_value"],
                int(fit is chosen),
            ])


def plot_fit(path: Path, rows: list[dict], xs: np.ndarray,
             fits: list[dict], chosen: dict, x0: float, dpi: int) -> None:
    means = np.array([row["mean"] for row in rows])
    half = np.array([row["half"] for row in rows])

    u = xs - x0
    u_grid = np.linspace(u.min(), u.max(), 300)
    x_grid = x0 + u_grid

    fig, (ax, ax_res) = plt.subplots(
        2, 1, figsize=(9.5, 7.0), dpi=dpi,
        gridspec_kw={"height_ratios": [3.0, 1.3]},
    )

    ax.errorbar(xs, means, yerr=half, fmt="o", capsize=5,
                color="#1f77b4", label="среднее Y на уровне, 95% ДИ",
                zorder=4)

    linear = fits[0]
    ax.plot(x_grid, np.polyval(linear["c"][::-1], u_grid), "--",
            color="#7f7f7f", lw=1.4,
            label=f"линейная: adj R²={linear['adj']:.4f}")

    if chosen["degree"] > 1:
        ax.plot(x_grid, np.polyval(chosen["c"][::-1], u_grid), "-",
                color="#d62728", lw=2.0,
                label=f"{chosen['name']}: adj R²={chosen['adj']:.4f}")
    else:
        ax.plot([], [], "-", color="#d62728", lw=2.0,
                label="лучшая модель — линейная")

    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("Y, сек")
    ax.set_title("Зависимость среднего времени ожидания Y от t_green")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="best")

    ax_res.axhline(0.0, color="#333333", lw=1.0)
    ax_res.vlines(xs, 0.0, chosen["residuals"], color="#d62728", lw=1.2)
    ax_res.scatter(xs, chosen["residuals"], s=26, color="#d62728",
                   zorder=3, label=f"остатки: {chosen['name']}")
    ax_res.set_xlabel("t_green, сек")
    ax_res.set_ylabel("Y − Ŷ, сек")
    ax_res.set_title(f"Остатки лучшей модели (RMSE={chosen['rmse']:.4f})")
    ax_res.grid(alpha=0.3)
    ax_res.legend(fontsize=8, loc="best")

    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    args = build_parser().parse_args()
    results = args.results
    out = args.out or results
    meta_path = results / "meta.csv"
    if not meta_path.exists():
        raise FileNotFoundError(f"нет файла: {meta_path}")

    meta = read_meta(meta_path)
    x0 = float(meta["x0"])
    xs, rows = level_table(meta, results)
    means = np.array([row["mean"] for row in rows])
    u = xs - x0

    fits = [fit_polynomial(u, means, degree) for degree in (1, 2, 3)]
    chosen = select_best(fits)

    print(f"Параметр: {meta['variable']}, x0={x0:g}, "
          f"delta={meta['delta']}, уровней={meta['levels']}, "
          f"реплик на уровень={meta['reps_per_level']}")
    print_levels(rows)
    print_fits(fits, chosen)

    print("\n=== Уравнения ===")
    for fit in fits:
        print(f"{fit['name']:<14} {equation(fit, x0)}")

    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "approximation_summary.csv"
    write_summary(summary_path, meta, fits, chosen)

    plot_path = out / "tgreen_approximation.png"
    plot_fit(plot_path, rows, xs, fits, chosen, x0, args.dpi)

    print("\n=== Вывод ===")
    if chosen["degree"] == 1:
        tests = [f for f in fits[1:] if not math.isnan(f["p_value"])]
        detail = "; ".join(
            f"{f['name']}: p={f['p_value']:.4f}, adj R²={f['adj']:.4f}"
            for f in tests
        )
        print("Линейная аппроксимация достаточна: добавление квадратичного "
              "и кубического членов статистически незначимо "
              f"({detail}).")
    else:
        previous = fits[chosen["degree"] - 2]
        print(f"Лучшее приближение — {chosen['name']} модель: "
              f"F={chosen['f']:.3f}, p={chosen['p_value']:.4f} < {ALPHA}, "
              f"adjusted R² вырос с {previous['adj']:.4f} "
              f"до {chosen['adj']:.4f} по сравнению с предыдущей "
              f"моделью ({previous['name']}).")
    print(f"Уравнение: {equation(chosen, x0)}")
    print(f"adj R²={chosen['adj']:.5f}, RMSE={chosen['rmse']:.5f}, "
          f"AICc={chosen['aicc']:.2f}")

    print(f"\nсводка: {summary_path}")
    print(f"график: {plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
