from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import matplotlib

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import responses as rs
import trace as tr


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analyze.py",
        description="Графики динамики откликов и таблица результатов по данным логгера.",
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="файлы с откликами: .csv или .jsonl")
    parser.add_argument("--out", type=Path, default=Path("charts"), help="папка для результатов (по умолчанию charts)")
    parser.add_argument("--label", default="", help="подпись в заголовках графиков")
    parser.add_argument("--dpi", type=int, default=150, help="разрешение png (по умолчанию 150)")
    parser.add_argument("--max-series", type=int, default=40, help="сколько отдельных прогонов рисовать (0 — все)")
    parser.add_argument("--no-summary", action="store_true", help="не создавать таблицу результатов")
    parser.add_argument("--no-finals", action="store_true", help="не создавать графики итогов по прогонам")
    parser.add_argument("--all-finals", action="store_true", help="графики итогов для всех откликов, а не только максимумов очереди")
    parser.add_argument("--show", action="store_true", help="показать окна matplotlib вместо сохранения в файлы")
    parser.add_argument("--strict", action="store_true", help="ненулевой код возврата при ошибках")
    return parser


def slug(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return cleaned.strip("_") or "run"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.show:
        matplotlib.use("Agg")
    import plots

    problems: list[str] = []
    try:
        runs, warnings = tr.load(args.inputs)
    except Exception as error:  # noqa: BLE001
        runs, warnings = [], [f"не удалось прочитать входные данные: {error}"]
    problems.extend(warnings)

    if not runs:
        for line in problems:
            print(f"предупреждение: {line}", file=sys.stderr)
        print("данные для откликов не найдены")
        return 1 if args.strict else 0

    args.out.mkdir(parents=True, exist_ok=True)
    prefix = slug(args.label) if args.label else slug(Path(args.inputs[0]).stem)

    plotted: list[str] = []
    for response in rs.RESPONSES:
        if not rs.available(response, runs):
            problems.append(f"отклик {response.key}: нет данных, график пропущен")
            continue
        try:
            path = args.out / f"{prefix}_{response.key}.png"
            plots.plot_dynamics(runs, response, path, label=args.label, dpi=args.dpi, max_series=args.max_series)
            plotted.append(path.name)

            wants_finals = not args.no_finals and (args.all_finals or response.kind == "максимум")
            if wants_finals and rs.final_values(runs, response).size:
                final_path = args.out / f"{prefix}_{response.key}_finals.png"
                plots.plot_final_values(runs, response, final_path, label=args.label, dpi=args.dpi)
                plotted.append(final_path.name)
        except Exception as error:  # noqa: BLE001
            problems.append(f"{response.key}: {error}")

    if not args.no_summary:
        try:
            rows = rs.summary_rows(runs)
            rs.write_summary_csv(args.out / f"{prefix}_summary.csv", rows)
            rs.write_summary_md(
                args.out / f"{prefix}_summary.md",
                rows,
                f"Отклики: {args.label}" if args.label else "Отклики",
            )
            plotted.append(f"{prefix}_summary.csv")
            plotted.append(f"{prefix}_summary.md")
        except Exception as error:  # noqa: BLE001
            problems.append(f"таблица результатов: {error}")

    for line in problems:
        print(f"предупреждение: {line}")
    for line in rs.text_summary(runs):
        print(line)
    print(f"результаты: {args.out}")
    for name in plotted:
        print(f"  {name}")

    if args.show:
        import matplotlib.pyplot as plt

        plt.show()

    return 1 if (problems and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
