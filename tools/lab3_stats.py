#!/usr/bin/env python3
import csv
import math
import os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

RESULTS = Path("../results")
FIGS = RESULTS / "figures"
FIGS.mkdir(exist_ok=True)

# ---------- утилиты ----------

def read_Y(path):
    ys = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            ys.append(float(row["Y"]))
    return np.array(ys)

def read_interval(path):
    # возвращает dict: rep -> (t[], y[], qA[], qB[])
    data = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rep = int(row["replication"])
            t = float(row["model_time"])
            y = float(row["Y_interval"])
            qa = float(row["queue_a"])
            qb = float(row["queue_b"])
            data.setdefault(rep, ([], [], [], []))
            data[rep][0].append(t)
            data[rep][1].append(y)
            data[rep][2].append(qa)
            data[rep][3].append(qb)
    return {r: tuple(np.array(x) for x in v) for r, v in data.items()}

# ---------- 1.1 ----------

def task_1_1():
    print("\n=== 1.1 Хи-квадрат на нормальность (n=180) ===")
    ys = read_Y(RESULTS / "lab3_base_n180_summary.csv")
    n = len(ys)
    mu, sd = ys.mean(), ys.std(ddof=1)
    print(f"n={n} mean={mu:.4f} std={sd:.4f} min={ys.min():.3f} max={ys.max():.3f}")

    # Стерджес
    k = int(np.ceil(1 + 3.322 * math.log10(n)))
    print(f"bins (Sturges) k={k}")

    # бины по равным вероятностям нормального закона, чтобы Ei были не малы
    # (иначе хвосты дают Ei < 5 и критерий врёт)
    qs = np.linspace(0, 1, k + 1)
    edges = stats.norm.ppf(qs, loc=mu, scale=sd)
    edges[0] = -np.inf
    edges[-1] = np.inf

    observed, _ = np.histogram(ys, bins=edges)
    expected = np.full(k, n / k)

    # объединяем бины с Ei < 5 (здесь не должно быть, но пусть)
    chi2 = ((observed - expected) ** 2 / expected).sum()
    dof = k - 1 - 2  # -2: оценили mu и sd
    p = 1 - stats.chi2.cdf(chi2, dof)
    chi2_cr = stats.chi2.ppf(0.95, dof)

    print(f"observed : {observed.tolist()}")
    print(f"expected : {expected.tolist()}")
    print(f"chi2 = {chi2:.4f}, dof = {dof}, chi2_cr(0.95) = {chi2_cr:.4f}, p = {p:.4f}")
    print("H0 (нормальность) " + ("ПРИНЯТА" if chi2 < chi2_cr else "ОТВЕРГНУТА"))

    # график
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(ys, bins=edges, edgecolor="black", density=True, alpha=0.7, label="эмпирика")
    xs = np.linspace(ys.min() - 2 * sd, ys.max() + 2 * sd, 300)
    ax.plot(xs, stats.norm.pdf(xs, mu, sd), "r-", lw=2, label="N(μ, σ)")
    ax.set_xlabel("Y, сек")
    ax.set_ylabel("плотность")
    ax.set_title(f"п.1.1: Y, n={n}, χ²={chi2:.2f} (dof={dof}), p={p:.3f}")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / "1_1_hist.png", dpi=120)
    plt.close(fig)

    return dict(n=n, mu=mu, sd=sd, chi2=chi2, dof=dof, p=p,
                accepted=bool(chi2 < chi2_cr))

# ---------- 1.2 ----------

def task_1_2():
    print("\n=== 1.2 Точечные и интервальные оценки (n=20) ===")
    ys = read_Y(RESULTS / "lab3_base_n20_summary.csv")
    n = len(ys)
    mu = ys.mean()
    s = ys.std(ddof=1)
    t_cr = stats.t.ppf(0.975, n - 1)
    half = t_cr * s / math.sqrt(n)
    lo, hi = mu - half, mu + half
    print(f"n={n} Y_bar={mu:.4f} s={s:.4f}")
    print(f"t_cr(0.975, {n-1}) = {t_cr:.4f}")
    print(f"ДИ 95%: [{lo:.4f}; {hi:.4f}]  полуширина={half:.4f}")
    print(f"относительная точность = {100*half/mu:.2f}%")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar([0], [mu], yerr=[half], fmt="o", capsize=8, color="C0")
    ax.set_xlim(-1, 1)
    ax.set_xticks([])
    ax.set_ylabel("Y, сек")
    ax.set_title(f"п.1.2: Ȳ={mu:.2f}, 95% ДИ=[{lo:.2f}; {hi:.2f}]")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIGS / "1_2_ci.png", dpi=120)
    plt.close(fig)

    return dict(n=n, mu=mu, s=s, t_cr=t_cr, lo=lo, hi=hi, half=half)

# ---------- 1.3 ----------

def task_1_3():
    print("\n=== 1.3 Точность от n, поиск n* для 5% ===")
    ns = [5, 10, 20, 30, 50, 100, 150, 200]
    rows = []
    for n in ns:
        ys = read_Y(RESULTS / f"lab3_precision/n{n}_summary.csv")
        mu = ys.mean()
        s = ys.std(ddof=1)
        t_cr = stats.t.ppf(0.975, len(ys) - 1)
        half = t_cr * s / math.sqrt(len(ys))
        eps = 100 * half / mu
        rows.append(dict(n=n, mu=mu, s=s, half=half, eps=eps))
        print(f"n={n:3d}  mean={mu:8.4f}  s={s:7.4f}  half={half:7.4f}  eps={eps:6.3f}%")

    # оценка n* по формуле: half ≈ t * s / sqrt(n), t→z=1.96 при больших n
    # eps(n) = 1.96 * s_inf / sqrt(n) / mu_inf  ≤ 5%
    # используем s, mu при n=200 как асимптотику
    s_inf = rows[-1]["s"]
    mu_inf = rows[-1]["mu"]
    z = 1.96
    n_star = (z * s_inf / (0.05 * mu_inf)) ** 2
    print(f"оценка n* (5%) ≈ {n_star:.1f}")

    # график
    fig, ax = plt.subplots(figsize=(8, 4.5))
    eps_arr = [r["eps"] for r in rows]
    ax.plot(ns, eps_arr, "o-", label="эмпирика ε(n)")
    nn = np.linspace(5, 220, 200)
    ax.plot(nn, 100 * z * s_inf / (np.sqrt(nn) * mu_inf), "r--",
            label="асимптотика 100·1.96·s/√n/Ȳ")
    ax.axhline(5, color="green", ls=":", label="5%")
    ax.axvline(n_star, color="green", ls=":", alpha=0.6)
    ax.set_xlabel("n (реплик)")
    ax.set_ylabel("относительная полуширина ДИ, %")
    ax.set_title(f"п.1.3: ε(n), n*≈{n_star:.0f}")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / "1_3_eps.png", dpi=120)
    plt.close(fig)

    return dict(rows=rows, n_star=n_star, s_inf=s_inf, mu_inf=mu_inf)

# ---------- 1.4 ----------

def task_1_4():
    print("\n=== 1.4 Переходный период (кумулятивное среднее) ===")
    data = read_interval(RESULTS / "lab3_transient/transient_interval.csv")
    print(f"реплик: {len(data)}")

    fig, ax = plt.subplots(figsize=(11, 5))

    # накладываем 10 кривых + их среднее
    all_t = None
    for rep, (t, y, qa, qb) in sorted(data.items()):
        ax.plot(t, y, lw=0.8, alpha=0.45, label=f"rep {rep}")
        if all_t is None:
            all_t = t

    # среднее по репликам в каждой точке t (для визуального плато)
    ys_matrix = np.array([y for _, (t, y, qa, qb) in sorted(data.items())])
    y_mean = ys_matrix.mean(axis=0)

    ax.plot(all_t, y_mean, "k-", lw=2.0, label="среднее по 10 репликам")
    ax.axvline(1200, color="red", ls="--", alpha=0.5, label="T=1200 (кандидат T_пер)")
    ax.set_xlabel("модельное время, сек")
    ax.set_ylabel("кумулятивное среднее ожидание, сек")
    ax.set_title("п.1.4: накопленное среднее Y(t) по 10 репликам")
    ax.legend(ncol=2, fontsize=7, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / "1_4_transient_cum.png", dpi=120)
    plt.close(fig)

    # T_пер: первая точка, после которой среднее по репликам
    # меняется меньше чем на eps за окно W
    W = 600        # окно, сек
    eps = 0.5      # порог, сек
    T_пер = None
    for i, t in enumerate(all_t):
        if t + W > all_t[-1]:
            break
        m1 = y_mean[i]
        m2 = y_mean[(all_t >= t + W)][0]
        if abs(m2 - m1) < eps:
            T_пер = t
            break

    print(f"T_пер (визуально, порог {eps} сек за {W} сек) ≈ {T_пер}")

    # для сравнения — статистика по двум окнам (тот же t-тест, но теперь по Y(t))
    for T in [200, 400, 600, 800, 1000, 1200, 1500, 2000, 3000]:
        a = y_mean[(all_t >= T) & (all_t < T + W)]
        b = y_mean[(all_t >= T + W) & (all_t < T + 2*W)]
        if len(a) < 5 or len(b) < 5:
            continue
        tval, pval = stats.ttest_ind(a, b, equal_var=False)
        print(f"T={T:5d}  n1={len(a):4d}  n2={len(b):4d}  "
              f"mean1={a.mean():7.3f}  mean2={b.mean():7.3f}  p={pval:.3f}")

    return dict(all_t=all_t, y_mean=y_mean, T_пер=T_пер)


# ---------- 1.6 ----------

def task_1_6():
    print("\n=== 1.6 Чувствительность (5 точек по lambda_a) ===")
    # ожидаемый порядок: x-2, x-1, x0, x1, x2
    points = [("x-2", 0.06), ("x-1", 0.07), ("x0", 0.08), ("x1", 0.09), ("x2", 0.10)]
    rows = []
    for name, lam in points:
        path = RESULTS / f"lab3_sensitivity/{name}_summary.csv"
        if not path.exists():
            print(f"  нет файла {path}, пропуск")
            continue
        ys = read_Y(path)
        rows.append(dict(name=name, lam=lam, n=len(ys),
                         mean=ys.mean(), s=ys.std(ddof=1)))
        print(f"{name:4s} lambda={lam:.2f}  n={len(ys):3d}  "
              f"mean={ys.mean():8.4f}  s={ys.std(ddof=1):7.4f}")

    if len(rows) < 2:
        return dict(rows=rows)

    means = np.array([r["mean"] for r in rows])
    y0 = next((r["mean"] for r in rows if r["name"] == "x0"), means.mean())
    d = 0.05 * y0  # «несущественная» погрешность 5%
    spread = means.max() - means.min()
    sensitive = spread > d

    print(f"\nY(x0) = {y0:.4f}  d = 5% = {d:.4f}")
    print(f"max(Ybar) - min(Ybar) = {spread:.4f}")
    print("модель " + ("ЧУВСТВИТЕЛЬНА" if sensitive else "НЕ ЧУВСТВИТЕЛЬНА")
          + " к lambda_a на масштабе δ")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    xs = [r["lam"] for r in rows]
    ms = [r["mean"] for r in rows]
    ss = [r["s"] for r in rows]
    ns_ = [r["n"] for r in rows]
    err = [1.96 * s / math.sqrt(n) for s, n in zip(ss, ns_)]
    ax.errorbar(xs, ms, yerr=err, fmt="o-", capsize=5)
    ax.axhline(y0, color="gray", ls=":", label=f"Ȳ(x0)={y0:.2f}")
    ax.axhspan(y0 - d, y0 + d, color="green", alpha=0.15, label=f"±{d:.2f} (5%)")
    ax.set_xlabel("lambda_a, маш/сек")
    ax.set_ylabel("Ȳ, сек")
    ax.set_title(f"п.1.6: чувствительность к lambda_a (spread={spread:.2f})")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGS / "1_6_sensitivity.png", dpi=120)
    plt.close(fig)

    return dict(rows=rows, y0=y0, d=d, spread=spread, sensitive=bool(sensitive))

# ---------- main ----------

def main():
    r11 = task_1_1()
    r12 = task_1_2()
    r13 = task_1_3()
    task_1_4()
    r16 = task_1_6()

    print("\n=== ИТОГ ===")
    print(f"1.1: χ²={r11['chi2']:.2f} (cr={stats.chi2.ppf(0.95, r11['dof']):.2f}), "
          f"p={r11['p']:.3f} → {'нормальность принята' if r11['accepted'] else 'нормальность отвергнута'}")
    print(f"1.2: Ȳ={r12['mu']:.3f}, 95% ДИ=[{r12['lo']:.3f}; {r12['hi']:.3f}]")
    print(f"1.3: n*≈{r13['n_star']:.0f} (5% точность)")
    print(f"1.6: spread={r16['spread']:.3f}, d={r16['d']:.3f} → "
          f"{'чувствительна' if r16['sensitive'] else 'не чувствительна'}")
    print(f"\nграфики: {FIGS}")

if __name__ == "__main__":
    main()