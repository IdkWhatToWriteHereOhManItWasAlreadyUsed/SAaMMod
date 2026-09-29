from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib
import numpy as np

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import responses as rs
import trace as tr


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="correlate.py",
        description="Корреляции откликов от интенсивности движения "
                    "(каждый csv — уровень интенсивности с повторными прогонами).",
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="csv повторов по каждому уровню")
    parser.add_argument("--lambdas", required=True, help="интенсивности уровней через запятую, по порядку inputs")
    parser.add_argument("--out", type=Path, default=Path("correlations"), help="папка для результатов")
    parser.add_argument("--label", default="", help="подпись в заголовках и именах файлов")
    parser.add_argument("--dpi", type=int, default=150, help="разрешение png (по умолчанию 150)")
    parser.add_argument("--show", action="store_true", help="показать окна matplotlib вместо сохранения")
    parser.add_argument("--strict", action="store_true", help="ненулевой код возврата при ошибках")
    return parser


def slug(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text.strip())
    return cleaned.strip("_") or "run"


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _pearson(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask].astype(float)
    y = y[mask].astype(float)
    n = x.size
    if n < 2:
        return float("nan"), float("nan")
    xm = x - x.mean()
    ym = y - y.mean()
    denom = math.sqrt(float((xm * xm).sum()) * float((ym * ym).sum()))
    if denom == 0:
        return float("nan"), float("nan")
    r = float((xm * ym).sum()) / denom
    t = r * math.sqrt((n - 2) / max(1.0 - r * r, 1e-12))
    p = 2.0 * (1.0 - _phi(abs(t)))
    return r, p


def _fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask].astype(float)
    y = y[mask].astype(float)
    if x.size < 2:
        return float("nan"), float("nan")
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def _format(value: float) -> str:
    if value is None or not np.isfinite(value):
        return ""
    return f"{value:.3f}"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        lambdas = [float(v) for v in args.lambdas.split(",")]
    except ValueError as error:
        print(f"ошибка: --lambdas: {error}", file=sys.stderr)
        return 1
    if len(lambdas) != len(args.inputs):
        print("ошибка: число значений --lambdas не совпадает с числом inputs", file=sys.stderr)
        return 1

    problems: list[str] = []
    runs: list[tr.Run] = []
    run_lambdas: list[float] = []
    for path, level_lambda in zip(args.inputs, lambdas):
        loaded, warnings = tr.load([path])
        problems.extend(warnings)
        for run in loaded:
            runs.append(run)
            run_lambdas.append(level_lambda)
    if not runs:
        print("данные для корреляций не найдены")
        return 1 if args.strict else 0

    lambdas = np.array(run_lambdas, dtype=float)
    args.out.mkdir(parents=True, exist_ok=True)
    prefix = slug(args.label) if args.label else "correlations"

    rows: list[dict[str, str]] = []
    plotted: list[str] = []
    for response in rs.RESPONSES:
        values = np.array(
            [run.last(response.final_column) for run in runs],
            dtype=float,
        )
        r, p = _pearson(lambdas, values)
        slope, intercept = _fit(lambdas, values)

        rows.append({
            "key": response.key,
            "title": response.title,
            "r": _format(r),
            "r2": _format(r * r if np.isfinite(r) else float("nan")),
            "p": _format(p),
            "slope": _format(slope),
            "intercept": _format(intercept),
        })

        if args.show or (np.isfinite(r) and np.isfinite(slope)):
            fig, ax = plt.subplots(figsize=(11.0, 6.2), dpi=args.dpi)
            ax.scatter(lambdas, values, s=22, alpha=0.45, edgecolors="none",
                       color=response.color, label="прогон")
            levels_mean_x: list[float] = []
            levels_mean_y: list[float] = []
            for level in sorted(set(run_lambdas)):
                mask = lambdas == level
                levels_mean_x.append(level)
                levels_mean_y.append(float(np.nanmean(values[mask])))
            ax.scatter(levels_mean_x, levels_mean_y, marker="o", s=70,
                       color=response.color, edgecolors="black", linewidth=0.8,
                       label="среднее по уровню")
            suffix = f" — {args.label}" if args.label else ""
            ax.set_title(f"{response.title}{suffix} (r = {r:.3f}, p = {p:.3g})",
                         fontsize=13, pad=12)
            ax.set_xlabel("Интенсивность движения λ, машин/мин")
            ax.set_ylabel(response.ylabel)
            ax.grid(True, alpha=0.25, linewidth=0.6)
            ax.set_axisbelow(True)
            ax.legend(loc="best", fontsize=9, framealpha=0.85)
            fig.tight_layout()
            if args.show:
                plt.show()
            else:
                out_path = args.out / f"{prefix}_{response.key}_vs_lambda.png"
                fig.savefig(out_path)
                plotted.append(out_path.name)
            plt.close(fig)

    csv_path = args.out / f"{prefix}_correlations.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = __import__("csv").writer(handle)
        writer.writerow(["отклик", "r", "r2", "p", "наклон", "сдвиг"])
        for row in rows:
            writer.writerow([row["title"], row["r"], row["r2"], row["p"],
                             row["slope"], row["intercept"]])
    plotted.append(csv_path.name)

    for line in problems:
        print(f"warning: {line}")
    print(f"уровней интенсивности: {len(args.inputs)}, прогонов всего: {len(runs)}")
    width = max(32, max(len(row["title"]) for row in rows) + 2)
    header = f"{'отклик':<{width}}{'r':>10}{'r²':>10}{'p':>12}{'наклон':>12}{'сдвиг':>12}"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row['title']:<{width}}{row['r']:>10}{row['r2']:>10}{row['p']:>12}"
              f"{row['slope']:>12}{row['intercept']:>12}")
    print(f"результаты: {args.out}")
    for name in plotted:
        print(f"  {name}")

    return 1 if (problems and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())