from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from responses import Response, accumulated_mean, common_grid, final_values
from trace import Run

FIGURE_SIZE = (11.0, 6.2)
ACCENT = "#111111"


def _subsample(runs: list[Run], limit: int) -> list[Run]:
    if limit <= 0 or len(runs) <= limit:
        return runs
    step = int(np.ceil(len(runs) / limit))
    return runs[::step]


def _title(response: Response, label: str) -> str:
    suffix = f" — {label}" if label else ""
    return f"{response.title}{suffix}"


def _style(ax: plt.Axes, response: Response, title: str) -> None:
    ax.set_title(title, fontsize=13, pad=12)
    ax.set_xlabel("Модельное время")
    ax.set_ylabel(response.ylabel)
    ax.grid(True, alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.margins(x=0.01)


def plot_dynamics(
    runs: list[Run],
    response: Response,
    out_path: Path,
    *,
    label: str = "",
    dpi: int = 150,
    max_series: int = 40,
) -> Path:
    grid = common_grid(runs)
    accumulated = accumulated_mean(runs, response, grid)
    single = len(runs) == 1
    shown = _subsample(runs, 1 if single else max_series)
    style = "steps-post" if response.step else "default"
    scatter = response.kind == "дискретный"

    fig, ax = plt.subplots(figsize=FIGURE_SIZE, dpi=dpi)
    value_label = "текущее значение отклика"
    mean_label = "накопленное среднее отклика"
    drawn_value = False
    drawn_mean = False
    for run in shown:
        if run.has(response.value):
            if scatter:
                ax.scatter(
                    run.times,
                    run.columns[response.value],
                    s=8,
                    linewidths=0,
                    alpha=0.85 if single else 0.30,
                    color=response.color,
                    marker="o",
                    label=value_label if not drawn_value else "_nolegend_",
                )
            else:
                ax.plot(
                    run.times,
                    run.columns[response.value],
                    drawstyle=style,
                    linewidth=1.0 if single else 0.7,
                    alpha=0.85 if single else 0.30,
                    color=response.color,
                    label=value_label if not drawn_value else "_nolegend_",
                )
            drawn_value = True
        if response.mean and run.has(response.mean):
            ax.plot(
                run.times,
                run.columns[response.mean],
                drawstyle=style,
                linewidth=2.0 if single else 0.7,
                alpha=0.9 if single else 0.45,
                color=ACCENT if single else response.color,
                linestyle="-" if single else "--",
                label=mean_label if not drawn_mean else "_nolegend_",
            )
            drawn_mean = True

    if not single and np.isfinite(accumulated).any():
        ax.plot(
            grid,
            accumulated,
            linewidth=2.4,
            color=ACCENT,
            label=f"накопленное среднее по прогонам (до t={grid[-1]:.1f})",
        )

    if response.mean is None:
        values = final_values(runs, response)
        if values.size:
            ax.axhline(values.mean(), color="#2ca02c", linestyle=":", linewidth=1.6, label=f"среднее по прогонам: {values.mean():.2f}")

    _style(ax, response, _title(response, label))
    ax.legend(loc="best", fontsize=9, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_final_values(
    runs: list[Run],
    response: Response,
    out_path: Path,
    *,
    label: str = "",
    dpi: int = 150,
) -> Path:
    values = final_values(runs, response)
    if values.size == 0:
        return out_path

    fig, ax = plt.subplots(figsize=(FIGURE_SIZE[0], max(3.2, 0.32 * values.size + 1.6)), dpi=dpi)
    positions = np.arange(1, values.size + 1)
    ax.barh(positions, values, height=0.7, color=response.color, alpha=0.75, label="значение от прогона")
    ax.axvline(values.mean(), color="#2ca02c", linestyle="--", linewidth=1.8, label=f"среднее = {values.mean():.3f}")
    ax.axvline(values.min(), color="#7f7f7f", linestyle=":", linewidth=1.2, label=f"минимум = {values.min():.3f}")
    ax.axvline(values.max(), color="#7f7f7f", linestyle=":", linewidth=1.2, label=f"максимум = {values.max():.3f}")

    ax.set_yticks(positions)
    if values.size <= 30:
        ax.set_yticklabels([str(i) for i in positions], fontsize=8)
    else:
        ax.set_yticklabels([])
    ax.set_ylim(0, values.size + 1)
    ax.set_title(_title(response, label) + " — итог по прогонам", fontsize=13, pad=12)
    ax.set_xlabel(response.ylabel)
    ax.set_ylabel("Прогон")
    ax.grid(True, axis="x", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
