#!/usr/bin/env python3
"""Пункт 4: двухфакторный эксперимент t_green × t_red.

Запускается без аргументов. Для symmetric и asymmetric читает
results/4_two_factor/<case>/g{T}_r{R}_summary.csv, считает комплексный
критерий

    C = wY * Y/Y_ref + wQ * Q/Q_ref + wP * P_ref/P

где Y — среднее ожидание, Q — максимальная очередь одной из сторон,
P — пропускная способность.
Чем меньше C, тем лучше. Веса и референсная точка лежат в
results/4_two_factor/criteria.csv; если файла нет, он создаётся
со значениями по умолчанию.

Строит поверхности C, Y, изолинии C и срезы по каждому фактору,
оценивает значимость t_green и t_red.

Требования: numpy, matplotlib.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results" / "4_two_factor"
CASES = ("symmetric", "asymmetric")

# Значения по умолчанию; их можно переопределить в criteria.csv.
DEFAULT_CRITERIA = {
    "weight_wait": 0.5,
    "weight_queue": 0.9,
    "weight_throughput": 0.2,
    "ref_t_green": 15.0,
    "ref_t_red": 40.0,
}


def level_tag(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value).replace(".", "p")


def read_criteria() -> dict[str, float]:
    path = RESULTS / "criteria.csv"
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            row = next(csv.DictReader(handle), None)
        if row:
            return {key: float(row[key]) for key in DEFAULT_CRITERIA}
    RESULTS.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(DEFAULT_CRITERIA))
        writer.writeheader()
        writer.writerow(DEFAULT_CRITERIA)
    return dict(DEFAULT_CRITERIA)


def read_levels(meta_path: Path) -> tuple[list[float], list[float], int]:
    with meta_path.open("r", encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle), None)
    if row is None:
        raise RuntimeError(f"{meta_path}: пустой meta.csv")

    def parse(text: str) -> list[float]:
        return [float(value) for value in text.strip("[]").split(";") if value]

    return parse(row["levels_x"]), parse(row["levels_y"]), int(row["reps_per_point"])


def read_point(path: Path) -> tuple[float, float, float, float, float]:
    ys: list[float] = []
    queue_a: list[float] = []
    queue_b: list[float] = []
    queue_max: list[float] = []
    passed: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            a = float(row["max_queue_a"])
            b = float(row["max_queue_b"])
            ys.append(float(row["Y"]))
            queue_a.append(a)
            queue_b.append(b)
            queue_max.append(max(a, b))
            passed.append(float(row["passed"]))
    if not ys:
        raise RuntimeError(f"{path}: нет данных")
    return (
        float(np.mean(ys)),
        float(np.mean(queue_a)),
        float(np.mean(queue_b)),
        float(np.mean(queue_max)),
        float(np.mean(passed)),
    )


def load_case(case: str, criteria: dict[str, float]):
    case_dir = RESULTS / case
    green_levels, red_levels, reps = read_levels(case_dir / "meta.csv")

    rows: list[dict[str, float]] = []
    for green in green_levels:
        for red in red_levels:
            path = case_dir / f"g{level_tag(green)}_r{level_tag(red)}_summary.csv"
            if not path.exists():
                raise FileNotFoundError(f"нет файла: {path}")
            y_mean, qa_mean, qb_mean, qmax_mean, p_mean = read_point(path)
            rows.append({
                "t_green": green,
                "t_red": red,
                "Y": y_mean,
                "max_queue_a": qa_mean,
                "max_queue_b": qb_mean,
                "max_queue": qmax_mean,
                "passed": p_mean,
            })

    ref = next(
        (row for row in rows
         if row["t_green"] == criteria["ref_t_green"]
         and row["t_red"] == criteria["ref_t_red"]),
        None,
    )
    if ref is None:
        raise RuntimeError(
            f"{case}: нет референсной точки "
            f"t_green={criteria['ref_t_green']}, t_red={criteria['ref_t_red']}"
        )

    y_ref = ref["Y"]
    q_ref = ref["max_queue"]
    p_ref = ref["passed"]
    for row in rows:
        row["C"] = (
            criteria["weight_wait"] * row["Y"] / y_ref
            + criteria["weight_queue"] * row["max_queue"] / q_ref
            + criteria["weight_throughput"] * p_ref / row["passed"]
        )

    def make_grid(field: str) -> np.ndarray:
        return np.array([
            [next(r[field] for r in rows
                  if r["t_green"] == g and r["t_red"] == red)
             for g in green_levels]
            for red in red_levels
        ])

    return {
        "green": np.array(green_levels),
        "red": np.array(red_levels),
        "reps": reps,
        "rows": rows,
        "C": make_grid("C"),
        "Y": make_grid("Y"),
        "max_queue_a": make_grid("max_queue_a"),
        "max_queue_b": make_grid("max_queue_b"),
        "max_queue": make_grid("max_queue"),
    }


def write_summary(cases: dict[str, dict]) -> None:
    path = RESULTS / "two_factor_summary.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "case", "t_green", "t_red", "Y", "max_queue_a",
            "max_queue_b", "max_queue", "passed", "C",
        ])
        for case, data in cases.items():
            for row in data["rows"]:
                writer.writerow([
                    case, row["t_green"], row["t_red"], row["Y"],
                    row["max_queue_a"], row["max_queue_b"],
                    row["max_queue"], row["passed"], row["C"],
                ])


def factor_effects(data: dict) -> dict[str, float]:
    c = data["C"]
    mean = float(c.mean())
    main_green = c.mean(axis=0)
    main_red = c.mean(axis=1)
    n_red, n_green = c.shape

    ss_green = float(n_red * np.sum((main_green - mean) ** 2))
    ss_red = float(n_green * np.sum((main_red - mean) ** 2))
    ss_total = float(np.sum((c - mean) ** 2))
    ss_interaction = max(0.0, ss_total - ss_green - ss_red)

    return {
        "mean_C": mean,
        "range_green": float(main_green.max() - main_green.min()),
        "range_red": float(main_red.max() - main_red.min()),
        "ss_green": ss_green,
        "ss_red": ss_red,
        "ss_interaction": ss_interaction,
        "ss_total": ss_total,
        "share_green": ss_green / ss_total if ss_total > 0 else 0.0,
        "share_red": ss_red / ss_total if ss_total > 0 else 0.0,
        "share_interaction": ss_interaction / ss_total if ss_total > 0 else 0.0,
    }


def write_effects(cases: dict[str, dict]) -> None:
    path = RESULTS / "two_factor_effects.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "case", "factor", "range_C", "ss_share", "mean_C",
            "significance",
        ])
        for case, data in cases.items():
            effects = data["effects"]
            stronger = "t_green" if effects["ss_green"] >= effects["ss_red"] else "t_red"
            for factor, range_key, share_key in (
                ("t_green", "range_green", "share_green"),
                ("t_red", "range_red", "share_red"),
                ("interaction", "0", "share_interaction"),
            ):
                writer.writerow([
                    case, factor,
                    effects[range_key] if range_key in effects else "",
                    effects[share_key],
                    effects["mean_C"],
                    stronger if factor == stronger else "",
                ])


def plot_surface_C(case: str, data: dict, out_dir: Path) -> None:
    green, red = data["green"], data["red"]
    x, y = np.meshgrid(green, red)
    z = data["C"]

    fig = plt.figure(figsize=(10.0, 7.0))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(x, y, z, cmap="viridis", edgecolor="k",
                           linewidth=0.25, alpha=0.92)
    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("t_red, сек")
    ax.set_zlabel("C")
    ax.set_title(f"{case}: поверхность критерия C")
    fig.colorbar(surf, ax=ax, shrink=0.6, label="C")
    fig.tight_layout()
    fig.savefig(out_dir / "surface_C.png")
    plt.close(fig)


def plot_surface_Y(case: str, data: dict, out_dir: Path) -> None:
    green, red = data["green"], data["red"]
    x, y = np.meshgrid(green, red)
    z = data["Y"]

    fig = plt.figure(figsize=(10.0, 7.0))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(x, y, z, cmap="plasma", edgecolor="k",
                           linewidth=0.25, alpha=0.92)
    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("t_red, сек")
    ax.set_zlabel("Y, сек")
    ax.set_title(f"{case}: поверхность среднего ожидания Y")
    fig.colorbar(surf, ax=ax, shrink=0.6, label="Y, сек")
    fig.tight_layout()
    fig.savefig(out_dir / "surface_Y.png")
    plt.close(fig)


def plot_surface_max_queue(case: str, data: dict, out_dir: Path,
                           key: str, filename: str, title: str,
                           cmap: str) -> None:
    green, red = data["green"], data["red"]
    x, y = np.meshgrid(green, red)
    z = data[key]

    fig = plt.figure(figsize=(10.0, 7.0))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(x, y, z, cmap=cmap, edgecolor="k",
                           linewidth=0.25, alpha=0.92)
    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("t_red, сек")
    ax.set_zlabel("машин")
    ax.set_title(f"{case}: {title}")
    fig.colorbar(surf, ax=ax, shrink=0.6, label="машин")
    fig.tight_layout()
    fig.savefig(out_dir / filename)
    plt.close(fig)


def plot_surface_max_queue_zoom(case: str, data: dict, out_dir: Path,
                                min_green: float = 30.0) -> None:
    mask = data["green"] >= min_green
    green = data["green"][mask]
    if green.size < 2:
        return
    red = data["red"]
    x, y = np.meshgrid(green, red)
    z = data["max_queue"][:, mask]

    fig = plt.figure(figsize=(10.0, 7.0))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(x, y, z, cmap="magma", edgecolor="k",
                           linewidth=0.3, alpha=0.92)
    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("t_red, сек")
    ax.set_zlabel("машин")
    ax.set_title(f"{case}: max queue, t_green >= {min_green:g}")
    fig.colorbar(surf, ax=ax, shrink=0.6, label="машин")
    fig.tight_layout()
    fig.savefig(out_dir / "surface_max_queue_zoom.png")
    plt.close(fig)


def plot_surface_max_queue_log(case: str, data: dict, out_dir: Path) -> None:
    green, red = data["green"], data["red"]
    x, y = np.meshgrid(green, red)
    z = np.log10(np.maximum(data["max_queue"], 1e-9))

    fig = plt.figure(figsize=(10.0, 7.0))
    ax = fig.add_subplot(111, projection="3d")
    surf = ax.plot_surface(x, y, z, cmap="magma", edgecolor="k",
                           linewidth=0.25, alpha=0.92)
    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("t_red, сек")
    ax.set_zlabel("log10(макс. очередь)")
    ax.set_title(f"{case}: логарифм максимальной очереди")
    fig.colorbar(surf, ax=ax, shrink=0.6, label="log10(машин)")
    fig.tight_layout()
    fig.savefig(out_dir / "surface_max_queue_log.png")
    plt.close(fig)


def plot_max_queue_slices(case: str, data: dict, out_dir: Path) -> None:
    green, red = data["green"], data["red"]
    z = data["max_queue"]

    fig, ax = plt.subplots(figsize=(9.0, 5.5))
    for index, red_value in enumerate(red):
        ax.plot(green, z[index], "o-", label=f"t_red={red_value:g}")
    ax.set_yscale("log")
    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("макс. очередь, машин (log)")
    ax.set_title(f"{case}: max queue по t_green для разных t_red")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "max_queue_slices.png")
    plt.close(fig)


def plot_contour_C(case: str, data: dict, out_dir: Path) -> None:
    green, red = data["green"], data["red"]
    z = data["C"]
    minimum = np.unravel_index(np.argmin(z), z.shape)

    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    contour = ax.contourf(green, red, z, levels=15, cmap="viridis")
    lines = ax.contour(green, red, z, levels=10, colors="black", linewidths=0.5)
    ax.clabel(lines, inline=True, fontsize=7)
    ax.scatter(green[minimum[1]], red[minimum[0]], color="red", s=60,
               zorder=5, label="минимум C")
    ax.set_xlabel("t_green, сек")
    ax.set_ylabel("t_red, сек")
    ax.set_title(f"{case}: изолинии критерия C")
    ax.legend(fontsize=8)
    fig.colorbar(contour, ax=ax, label="C")
    fig.tight_layout()
    fig.savefig(out_dir / "contour_C.png")
    plt.close(fig)


def plot_slices(case: str, data: dict, out_dir: Path) -> None:
    green, red = data["green"], data["red"]
    z = data["C"]

    fig, (ax_g, ax_r) = plt.subplots(1, 2, figsize=(12.0, 5.0))
    for index, red_value in enumerate(red):
        ax_g.plot(green, z[index], "o-", label=f"t_red={red_value:g}")
    ax_g.set_xlabel("t_green, сек")
    ax_g.set_ylabel("C")
    ax_g.set_title(f"{case}: C от t_green")
    ax_g.legend(fontsize=7)
    ax_g.grid(alpha=0.3)

    for index, green_value in enumerate(green):
        ax_r.plot(red, z[:, index], "o-", label=f"t_green={green_value:g}")
    ax_r.set_xlabel("t_red, сек")
    ax_r.set_ylabel("C")
    ax_r.set_title(f"{case}: C от t_red")
    ax_r.legend(fontsize=7)
    ax_r.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_dir / "effect_slices.png")
    plt.close(fig)


def main() -> int:
    criteria = read_criteria()
    cases: dict[str, dict] = {}

    for case in CASES:
        data = load_case(case, criteria)
        data["effects"] = factor_effects(data)
        data["out_dir"] = RESULTS / case
        data["out_dir"].mkdir(parents=True, exist_ok=True)
        cases[case] = data

        minimum = np.unravel_index(np.argmin(data["C"]), data["C"].shape)
        print(f"\n=== {case} ===")
        print(f"точек: {data['C'].size}, реплик на точку: {data['reps']}")
        print(f"минимум C: t_green={data['green'][minimum[1]]:g}, "
              f"t_red={data['red'][minimum[0]]:g}, "
              f"C={data['C'][minimum]:.4f}")
        effects = data["effects"]
        print(f"размах C по t_green: {effects['range_green']:.4f}, "
              f"доля SS: {effects['share_green']:.3f}")
        print(f"размах C по t_red:   {effects['range_red']:.4f}, "
              f"доля SS: {effects['share_red']:.3f}")
        print(f"взаимодействие: доля SS: {effects['share_interaction']:.3f}")
        stronger = "t_green" if effects["ss_green"] >= effects["ss_red"] else "t_red"
        print(f"более значимый фактор: {stronger}")

        plot_surface_C(case, data, data["out_dir"])
        plot_surface_Y(case, data, data["out_dir"])
        plot_surface_max_queue(case, data, data["out_dir"],
                               "max_queue_a", "surface_max_queue_a.png",
                               "максимальная очередь A", "Blues")
        plot_surface_max_queue(case, data, data["out_dir"],
                               "max_queue_b", "surface_max_queue_b.png",
                               "максимальная очередь B", "Reds")
        plot_surface_max_queue(case, data, data["out_dir"],
                               "max_queue", "surface_max_queue.png",
                               "максимальная очередь одной из сторон", "magma")
        plot_surface_max_queue_zoom(case, data, data["out_dir"])
        plot_surface_max_queue_log(case, data, data["out_dir"])
        plot_max_queue_slices(case, data, data["out_dir"])
        plot_contour_C(case, data, data["out_dir"])
        plot_slices(case, data, data["out_dir"])

    write_summary(cases)
    write_effects(cases)
    print(f"\nсводка: {RESULTS / 'two_factor_summary.csv'}")
    print(f"эффекты: {RESULTS / 'two_factor_effects.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
