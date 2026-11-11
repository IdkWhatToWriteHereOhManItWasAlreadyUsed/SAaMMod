#!/usr/bin/env python3
# ЛР3: анализ стационарного состояния ИМ.
# п.1.4: Y_interval — честное среднее за интервал (только машины, начавшие
# движение в интервале), Y_cum — кумулятив (только для визуализации плато).
import csv
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

RESULTS = Path("../results")
FIGS = RESULTS / "figures"
FIGS.mkdir(exist_ok=True)

# Длительность эталонного прогона (сек) — должна совпадать с RUN_TIME
# в src/main.cpp и с точкой T{REF_RUN} в результатах п.1.4b.
REF_RUN = 10000
# Принятое время установления модели (сек) для п.1.4 и п.1.5.
T_SETTLE = 1200.0
# Минимальная длина каждого из двух сравниваемых отрезков в п.1.5, сек.
MIN_CONTINUOUS_SEGMENT = 300.0
# Допустимое относительное отклонение среднего по участку в п.1.5.
MEAN_TOL = 0.05

# ---------- утилиты ----------

def read_Y(path):
    ys = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            ys.append(float(row["Y"]))
    return np.array(ys)

def read_intervals(path):
    # dict rep -> (t, Y_interval [NaN для пустых], Y_cum, w_count_interval)
    data = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rep = int(row["replication"])
            t = float(row["model_time"])
            yi = np.nan if row["Y_interval"] == "NA" else float(row["Y_interval"])
            yc = float(row["Y_cum"])
            wc = int(row["w_count_interval"])
            data.setdefault(rep, ([], [], [], []))
            data[rep][0].append(t)
            data[rep][1].append(yi)
            data[rep][2].append(yc)
            data[rep][3].append(wc)
    return {r: tuple(np.array(x) for x in v) for r, v in data.items()}

def smooth(x, y, half_width):
    # скользящее среднее по окну [x-w, x+w]; NaN игнорируются
    out = np.full_like(y, np.nan, dtype=float)
    for i, xi in enumerate(x):
        m = (x >= xi - half_width) & (x <= xi + half_width)
        if m.any() and np.any(~np.isnan(y[m])):
            out[i] = np.nanmean(y[m])
    return out

def willink_ci(values, alpha=0.05):
    """Асимметричный доверительный интервал по методу Уиллинка.
    Элемент.Done coroutine-а: a — нормированная мера асимметрии (по μ3)."""
    x = np.asarray(values, dtype=float)
    n = len(x)
    mean = x.mean()
    sd = x.std(ddof=1)
    t_value = stats.t.ppf(1 - alpha / 2, n - 1)

    # третий центральный момент, несмещённая оценка
    mu3 = np.sum((x - mean) ** 3) * n / ((n - 1) * (n - 2))
    a = mu3 / (6 * math.sqrt(n) * sd ** 3)
    if abs(a) < 1e-12:          # асимметрии нет — симметричный t-интервал
        half = t_value * sd / math.sqrt(n)
        return mean - half, mean + half, 0.0

    g_left = ((1 + 6 * a * (t_value - a)) ** (1.0 / 3) - 1) * 0.5 / a
    g_right = ((1 + 6 * a * (-t_value - a)) ** (1.0 / 3) - 1) * 0.5 / a
    return mean - g_left * sd / math.sqrt(n), \
           mean - g_right * sd / math.sqrt(n), a

# ---------- 1.1 ----------

def task_1_1():
    print("\n=== 1.1 Хи-квадрат на нормальность (n=500) ===")
    ys = read_Y(RESULTS / "lab3_base_n500_summary.csv")
    n = len(ys)
    mu, sd = ys.mean(), ys.std(ddof=1)
    print(f"n={n} mean={mu:.4f} std={sd:.4f} min={ys.min():.3f} max={ys.max():.3f}")

    k = int(np.ceil(1 + 3.322 * math.log10(n)))          # Стерджес
    print(f"bins (Sturges) k={k}")

    # ---------- вариант 1 (лекционный): бины РАВНОЙ ШИРИНЫ ----------
    # Pi — вероятность попадания N(mu, sd) в интервал [edge_i, edge_{i+1})
    width_edges = np.linspace(ys.min(), ys.max(), k + 1)
    cdf = stats.norm.cdf(width_edges, loc=mu, scale=sd)
    probs = np.diff(cdf)                                  # Pi каждого бина
    probs[0] += cdf[0]                                    # хвост (-inf, e1)
    probs[-1] += 1 - cdf[-1]                              # хвост (ek, +inf)
    observed_w, _ = np.histogram(ys, bins=width_edges)
    expected_w_n = probs * n

    # объединение бинов с E < 5 (стандартное правило применения критерия);
    # хвостовой остаток присоединяется к последнему бину
    obs_l, exp_p_l = [], []
    cur_n, cur_p = 0, 0.0
    for i in range(k):
        cur_n += observed_w[i]
        cur_p += probs[i]
        residue = (i == k - 1)
        if cur_p * n >= 5 or residue:
            if residue and obs_l:
                obs_l[-1] += cur_n
                exp_p_l[-1] += cur_p
            else:
                obs_l.append(cur_n)
                exp_p_l.append(cur_p)
            cur_n, cur_p = 0, 0.0
    obs_l = np.array(obs_l)
    exp_p_l = np.array(exp_p_l)
    exp_l = exp_p_l * n
    dev_l = (obs_l - exp_l) ** 2 / exp_l
    k_eff = len(obs_l)

    print(f"\nосновной тест: бины равной ширины (Стерджес), Pi по N(mu, sd); "
          f"объединение бинов с E<5: {k} → {k_eff} интервалов")
    print(f"{'инт':>3} {'ni':>4} {'ni/n':>7} {'Pi':>7} {'nPi':>8} {'взнос':>8}")
    for i in range(k_eff):
        print(f"{i+1:3d} {obs_l[i]:4d} {obs_l[i]/n:7.3f} {exp_p_l[i]:7.3f} "
              f"{exp_l[i]:8.1f} {dev_l[i]/n:8.2f}")
    chi2 = dev_l.sum()
    dof = k_eff - 1 - 2             # -2 за оценённые mu и sd
    p = 1 - stats.chi2.cdf(chi2, dof)
    chi2_cr = stats.chi2.ppf(0.95, dof)
    accepted = chi2 < chi2_cr
    print(f"χ²={chi2:.2f}, dof={dof}, χ²кр(0.95)={chi2_cr:.2f}, p={p:.3f} → "
          f"нормальность {'ПРИНЯТА' if accepted else 'ОТВЕРГНУТА'}")

    # ---------- вариант 2 (контроль): бины равных вероятностей ----------
    # Pi = 1/k, Ei = n/k >= 5 — нечувствителен к редким хвостам
    qs = np.linspace(0, 1, k + 1)
    edges = stats.norm.ppf(qs, loc=mu, scale=sd)
    edges[0], edges[-1] = -np.inf, np.inf
    observed_q, _ = np.histogram(ys, bins=edges)
    exp_q = np.full(k, n / k)
    chi2_q = ((observed_q - exp_q) ** 2 / exp_q).sum()
    dof_q = k - 1 - 2
    p_q = 1 - stats.chi2.cdf(chi2_q, dof_q)
    acc_q = chi2_q < stats.chi2.ppf(0.95, dof_q)
    print(f"\nконтроль (бины равных вероятностей, Pi={1.0/k:.3f}): "
          f"χ²={chi2_q:.3f}, dof={dof_q}, p={p_q:.3f} → "
          f"{'ПРИНЯТА' if acc_q else 'ОТВЕРГНУТА'}")

    # границы графика — равная ширина (вариант 1)
    pe = width_edges.copy()

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(ys, bins=pe, edgecolor="black", density=True, alpha=0.7,
            label="эмпирика")
    xs = np.linspace(pe[0], pe[-1], 300)
    ax.plot(xs, stats.norm.pdf(xs, mu, sd), "r-", lw=2, label="N(μ, σ)")
    ax.set_xlabel("Y, сек"); ax.set_ylabel("плотность")
    ax.set_title(f"п.1.1: Y, n={n}, χ²={chi2:.2f} (dof={dof}), "
                 f"χ²кр={chi2_cr:.2f}, p={p:.3f}")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "1_1_hist.png", dpi=120); plt.close(fig)

    return dict(n=n, mu=mu, sd=sd, chi2=chi2, chi2_check=chi2_q, dof=dof,
                p=p, accepted=accepted)

# ---------- 1.2 ----------

def task_1_2():
    print("\n=== 1.2 Точечные и интервальные оценки (n=20) ===")
    ys = read_Y(RESULTS / "lab3_base_n20_summary.csv")
    n = len(ys)
    mu, s = ys.mean(), ys.std(ddof=1)
    t_cr = stats.t.ppf(0.975, n - 1)
    half = t_cr * s / math.sqrt(n)
    lo, hi = mu - half, mu + half
    print(f"n={n} Y_bar={mu:.4f} s={s:.4f}  t_cr(0.975,{n-1})={t_cr:.4f}")
    print(f"t-ДИ 95%: [{lo:.4f}; {hi:.4f}]  полуширина={half:.4f}  "
          f"точность={100 * half / mu:.2f}%")

    wl, wh, a = willink_ci(ys)
    print(f"асимметрия: a={a:.4f} (μ3={np.sum((ys - mu) ** 3) * n / ((n - 1) * (n - 2)):.2f})")
    print(f"ДИ Уиллинка 95%: [{wl:.4f}; {wh:.4f}]  "
          f"лев. полуширина={mu - wl:.4f}, прав.={wh - mu:.4f}")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    # автоматические оси: симметрично вокруг Ȳ с запасом по самому
    # широкому интервалу и по сырым данным
    span = max(half, wh - mu, mu - wl,
               ys.max() - mu, mu - ys.min()) * 1.4
    ax.set_ylim(min(mu - span, ys.min() - 0.3), max(mu + span, ys.max() + 0.3))

    # все реплики как точки (лёгкий джиттер по X, чтобы не слипались)
    rng = np.random.default_rng(42)
    x_data = -0.30
    jit = rng.uniform(-0.055, 0.055, len(ys))
    ax.scatter(x_data + jit, ys, s=26, color="gray", alpha=0.7, zorder=2)
    ax.hlines(ys.mean(), x_data - 0.10, x_data + 0.10, color="k",
              lw=1.6, zorder=3)

    ax.errorbar([0], [mu], yerr=[[mu - wl], [wh - mu]], fmt="o", capsize=8,
                color="C1", zorder=4)
    ax.errorbar([0.18], [mu], yerr=half, fmt="o", capsize=8, color="C0",
                zorder=4)
    ax.axhspan(wl, wh, xmin=0.30, xmax=0.42, color="C1", alpha=0.12, zorder=1)
    ax.axhspan(lo, hi, xmin=0.42, xmax=0.54, color="C0", alpha=0.12, zorder=1)
    ax.text(0, wh + span * 0.03, f"Уиллинк\n[{wl:.2f}; {wh:.2f}]",
            ha="center", va="bottom", fontsize=8, color="C1")
    ax.text(0.18, lo - span * 0.03, f"t-Стьюдент\n[{lo:.2f}; {hi:.2f}]",
            ha="center", va="top", fontsize=8, color="C0")
    ax.axhline(mu, color="gray", ls=":", lw=1)
    ax.set_xlim(-0.55, 0.55)
    ax.set_xticks([x_data, 0, 0.18])
    ax.set_xticklabels([f"реплики (n={len(ys)})", "Уиллинк", "t-Стьюдент"])
    ax.set_ylabel("Y, сек")
    ax.set_title(f"п.1.2: Ȳ={mu:.2f} сек, n=20, 95%")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIGS / "1_2_ci.png", dpi=120); plt.close(fig)

    return dict(n=n, mu=mu, s=s, lo=lo, hi=hi, wl=wl, wh=wh, a=a)

# ---------- 1.3 ----------

def task_1_3():
    print("\n=== 1.3 Точность от n, поиск n* для 5% ===")
    ns = [5, 10, 20, 30, 50, 100, 150, 200]
    rows = []
    for n in ns:
        ys = read_Y(RESULTS / f"lab3_precision/n{n}_summary.csv")
        mu, s = ys.mean(), ys.std(ddof=1)
        t_cr = stats.t.ppf(0.975, n - 1)
        half = t_cr * s / math.sqrt(n)
        eps = 100 * half / mu
        rows.append(dict(n=n, mu=mu, s=s, half=half, eps=eps))
        print(f"n={n:3d}  mean={mu:8.4f}  s={s:7.4f}  half={half:7.4f}  "
              f"eps={eps:6.3f}%")

    s_inf, mu_inf = rows[-1]["s"], rows[-1]["mu"]

    # n*: минимальное n, при котором t(0.975, n-1)*s_inf/sqrt(n) <= 0.05*mu_inf
    # (итерациями с t-квантилем, а не z=1.96, — согласовано с эмпирикой ε(n))
    n_star = None
    for n in range(2, 20001):
        if stats.t.ppf(0.975, n - 1) * s_inf / math.sqrt(n) <= 0.05 * mu_inf:
            n_star = n
            break
    print(f"оценка n* (5%, итерации с t) ≈ {n_star}")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(ns, [r["eps"] for r in rows], "o-", label="эмпирика ε(n)")
    nn = np.linspace(5, 220, 300)
    ax.plot(nn, 100 * 1.96 * s_inf / (np.sqrt(nn) * mu_inf), "r-", lw=1,
            label="асимптотика 100·1.96·s/√n/Ȳ")
    ax.axhline(5, color="green", ls=":", label="5%")
    ax.axvline(n_star, color="green", ls=":", alpha=0.6, label=f"n*≈{n_star}")
    ax.set_xlabel("n (реплик)"); ax.set_ylabel("относительная полуширина ДИ, %")
    ax.set_title(f"п.1.3: ε(n), n*≈{n_star}")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "1_3_eps.png", dpi=120); plt.close(fig)

    return dict(rows=rows, n_star=n_star)

# ---------- 1.4 ----------

def task_1_4():
    """П.1.4: время установления принято равным T0=1200.

    Статистический поиск T_пер больше не используется: T0 задан.
    Здесь показываем переходный процесс и уровень отклика после T0.
    """
    print(f"\n=== 1.4 Переходный период: принято T0={T_SETTLE:.0f} сек ===")
    data = read_intervals(RESULTS / "lab3_transient/transient_interval.csv")
    reps = sorted(data)
    print(f"реплик: {len(reps)}")

    t = data[reps[0]][0]
    Y_int = np.vstack([data[r][1] for r in reps])   # NaN — пустой интервал
    Y_cum = np.vstack([data[r][2] for r in reps])
    print(f"пустых интервалов (NA): {int(np.isnan(Y_int).sum())} из {Y_int.size}")

    W = 600          # окно оценки уровня после T0, сек
    HALF_W = 300     # полуширина сглаживания, сек

    # взвешенные по числу машин средние — согласованы с семантикой Y
    def wmean(rep, tt0, tt1):
        yi, wc = data[rep][1], data[rep][3]
        m = (t >= tt0) & (t < tt1) & ~np.isnan(yi)
        c = wc[m]
        return float(np.sum(yi[m] * c) / c.sum()) if c.sum() > 0 else np.nan

    def rolling_weighted(rep, half):
        out = np.full(len(t), np.nan)
        for i, ti in enumerate(t):
            out[i] = wmean(rep, ti - half, ti + half)
        return out

    T0 = float(T_SETTLE)
    steady_level = np.nanmean([wmean(r, T0, T0 + W) for r in reps])
    print(f"T0={T0:.0f} сек (принято по заданию); уровень Y на "
          f"[{T0:.0f},{T0 + W:.0f}) ≈ {steady_level:.1f} сек")

    # --- график: сглаженные взвешенные кривые по репликам + их среднее ---
    curves = np.array([rolling_weighted(r, HALF_W) for r in reps])
    curve_mean = np.nanmean(curves, axis=0)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, r in enumerate(reps):
        ax.plot(t, curves[i], lw=0.7, alpha=0.35)
    ax.plot(t, curve_mean, "b-", lw=2.2,
            label="Y_interval (взвеш. по числу машин), среднее по репликам")
    ax.plot(t, smooth(t, Y_cum.mean(axis=0), HALF_W), "k--", lw=1.5,
            label="Y_cum кумулятив (визуализация)")
    ax.axvline(T0, color="red", ls="--", lw=1.2,
               label=f"T0 = {T0:.0f} сек (принято)")
    ax.set_xlabel("модельное время, сек")
    ax.set_ylabel("среднее ожидание, сек")
    ax.set_title(f"п.1.4: T0={T0:.0f} сек принято; "
                 f"взвешенные Y_interval (окно {2*HALF_W} с)")
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "1_4_transient.png", dpi=120)
    plt.close(fig)

    return dict(T_detect=T0, steady_level=steady_level)

# ---------- 1.4b: гипотеза об уменьшении времени прогона ----------

def task_1_4b():
    """П.1.4: сокращение рантайма при принятом T0=1200.

    Эталон — прогон длительностью REF_RUN; для кандидата T сравниваем
    Y на [T0,T] с Y на [T0,REF_RUN]. Используются interval-файлы,
    поэтому переходный процесс в выборки не попадает.
    T_short — минимальная длительность, для которой T и следующий
    (более длинный) кандидат однородны с эталоном.
    """
    print(f"\n=== 1.4 Сокращение рантайма при T0={T_SETTLE:.0f} ===")
    ref_path = RESULTS / f"lab3_shortened/T{REF_RUN}_interval.csv"
    if not ref_path.exists():
        print(f"п.1.4: нет {ref_path} — пропуск")
        return None

    def window_means(path, a, b):
        data = read_intervals(path)
        vals = []
        for rep in sorted(data):
            t, yi, _yc, wc = data[rep]
            m = (t >= a) & (t < b) & ~np.isnan(yi)
            w = wc[m]
            vals.append(float(np.sum(yi[m] * w) / w.sum())
                        if w.sum() > 0 else np.nan)
        out = np.array(vals)
        return out[~np.isnan(out)]

    ref = window_means(ref_path, T_SETTLE, REF_RUN)
    n0 = len(ref)
    mu0, s0 = ref.mean(), ref.std(ddof=1)
    print(f"эталон {Y0_LABEL}: T={REF_RUN}, Y на "
          f"[{T_SETTLE:.0f},{REF_RUN}], n={n0}, "
          f"mean={mu0:.4f}, s={s0:.4f}")

    rows = []
    for path in sorted((RESULTS / "lab3_shortened").glob("T*_interval.csv")):
        Ti = int(path.stem.replace("_interval", "")[1:])
        if Ti <= T_SETTLE or Ti == REF_RUN:
            continue
        ys = window_means(path, T_SETTLE, Ti)
        if len(ys) < 2:
            continue
        muT, sT = ys.mean(), ys.std(ddof=1)
        # 1) F-тест равенства дисперсий
        F = max(s0, sT) ** 2 / min(s0, sT) ** 2
        v1, v2 = ((n0 - 1, len(ys) - 1) if s0 >= sT
                  else (len(ys) - 1, n0 - 1))
        F_cr = stats.f.ppf(0.95, v1, v2)
        var_equal = F <= F_cr
        # 2) равенство средних: t при равных дисперсиях, иначе Уэлч
        if var_equal:
            sv = ((n0 - 1) * s0 ** 2 + (len(ys) - 1) * sT ** 2) \
                / (n0 + len(ys) - 2)
            tval = (mu0 - muT) / math.sqrt(sv * (1 / n0 + 1 / len(ys)))
            dof = n0 + len(ys) - 2
            pval = 2 * (1 - stats.t.cdf(abs(tval), dof))
            test = "t"
        else:
            tval, pval = stats.ttest_ind(ref, ys, equal_var=False)
            test = "Welch"
        homo = pval >= 0.05
        rows.append(dict(T=Ti, mu=muT, s=sT, n=len(ys), F=F, F_cr=F_cr,
                         var_equal=var_equal, test=test, t=tval,
                         p=pval, homo=homo))
        print(f"T={Ti:5d} окно=[{T_SETTLE:.0f},{Ti})  "
              f"mean={muT:8.4f} s={sT:7.4f} | "
              f"F={F:5.3f} (кр={F_cr:5.3f} → "
              f"{'дисперсии равны' if var_equal else 'дисперсии РАЗНЫЕ'}) | "
              f"{test}: t={tval:6.3f} p={pval:5.3f} → "
              f"{'ОДНОРОДНЫ' if homo else 'различаются'}")

    rows.sort(key=lambda r: r["T"])
    # T_short: первая длительность, которая однородна вместе со следующим
    # более длинным кандидатом (защита от одиночного случайного прохода)
    T_short = None
    for i, r in enumerate(rows):
        if not (r["var_equal"] and r["homo"]):
            continue
        nxt = rows[i + 1:i + 2]
        if all(rr["var_equal"] and rr["homo"] for rr in nxt):
            T_short = r["T"]
            break

    window = (T_short - T_SETTLE) if T_short is not None else None
    if T_short is None:
        print("\nT_short не найден: нет устойчиво однородной длительности")
    else:
        print(f"\nT_short = {T_short} сек (полная длительность прогона); "
              f"окно наблюдения после T0 = {window:.0f} сек")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ts_ = [r["T"] for r in rows]
    ms_ = [r["mu"] for r in rows]
    err_ = [stats.t.ppf(0.975, r["n"] - 1) * r["s"] / math.sqrt(r["n"])
            for r in rows]
    ref_err = stats.t.ppf(0.975, n0 - 1) * s0 / math.sqrt(n0)
    ax.errorbar(ts_, ms_, yerr=err_, fmt="o-", capsize=4,
                label="{YT}, Y на [T0,T]")
    ax.errorbar([REF_RUN], [mu0], yerr=ref_err, fmt="s", capsize=4,
                color="red", label=f"{{Y0}} (T={REF_RUN}, эталон)")
    ax.axhline(mu0, color="gray", ls=":")
    if T_short:
        ax.axvline(T_short, color="green", ls=":", alpha=0.8,
                   label=f"T_short={T_short} (окно {window:.0f} с)")
    ax.set_xlabel("T окончания прогона, сек")
    ax.set_ylabel(f"Ȳ на [{T_SETTLE:.0f},T], сек")
    ax.set_title(f"п.1.4: сокращение рантайма при T0={T_SETTLE:.0f}")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "1_4b_shortened.png", dpi=120)
    plt.close(fig)

    return dict(ref_run=REF_RUN, t0=T_SETTLE, t_short=T_short,
                window=window, rows=rows)


def task_1_5(t_short=None):
    """П.1.5: однородность средних и дисперсий на 100 участках.

    После T0=1200 берутся N=100 последовательных участков по
    W = T_short - T0 секунд. Средние и дисперсии считаются взвешенными
    по числу машин (w_count_interval), как в п.1.4.
    Критерий п.1.5: среднее каждого участка должно отличаться от общего
    среднего не более чем на MEAN_TOL·100% (5%).
    Welch-ANOVA, Levene и Bartlett выводятся как диагностика.
    """
    if t_short is None:
        raise RuntimeError("task_1_5: нужен T_short из п.1.4")

    T0 = float(T_SETTLE)
    W = float(t_short) - T0
    N = 100
    if W < MIN_CONTINUOUS_SEGMENT:
        print(f"п.1.5: окно {W:.0f} сек < {MIN_CONTINUOUS_SEGMENT:.0f} — пропуск")
        return None

    required = T0 + N * W
    path = RESULTS / "lab3_continuous/continuous_interval.csv"
    if not path.exists():
        print(f"п.1.5: нет {path} — пропуск")
        return None
    data = read_intervals(path)
    reps = sorted(data)
    if not reps:
        print(f"п.1.5: в {path} нет реплик — пропуск")
        return None
    if len(reps) != 1:
        print(f"п.1.5: ожидался один длинный прогон, найдено {len(reps)}; "
              f"используется реплика {reps[0]}")
    rep = reps[0]
    t, yi, _yc, wc = data[rep]
    T_end = float(t[-1])

    if T_end < required - 1e-9:
        print(f"п.1.5: данных до {T_end:.0f} сек, нужно {required:.0f} — пропуск")
        return None

    print(f"\n=== 1.5 Проверка средних: {N} участков по {W:.0f} с "
          f"после T0={T0:.0f}, допуск ±{100 * MEAN_TOL:.0f}% ===")
    print(f"диапазон: [{T0:.0f},{required:.0f}), данных до {T_end:.0f} сек")

    groups = []
    rows = []
    for k in range(N):
        a = T0 + k * W
        b = a + W
        m = (t >= a) & (t < b) & ~np.isnan(yi)
        vals = yi[m]
        weights = wc[m].astype(int)
        n_cars = int(weights.sum())
        if len(vals) < 2 or n_cars < 2:
            print(f"п.1.5: в участке {k + 1} слишком мало данных — пропуск")
            return None

        mean_w = float(np.sum(vals * weights) / n_cars)
        var_w = float(np.sum(weights * (vals - mean_w) ** 2) / (n_cars - 1))

        # взвешенная псевдовыборка: каждый интервал повторяется по числу
        # машин; её среднее совпадает с wmean из п.1.4
        groups.append(np.repeat(vals, weights))
        rows.append(dict(segment=k + 1, start=a, end=b,
                         n_intervals=len(vals), n_cars=n_cars,
                         mean=mean_w, var=var_w))

    mean_values = np.array([r["mean"] for r in rows])
    var_values = np.array([r["var"] for r in rows])
    all_values = np.concatenate(groups)
    overall_mean = float(np.mean(all_values))
    overall_var = float(np.var(all_values, ddof=1))
    min_n = min(r["n_cars"] for r in rows)
    max_n = max(r["n_cars"] for r in rows)
    min_int = min(r["n_intervals"] for r in rows)
    max_int = max(r["n_intervals"] for r in rows)

    # критерий: |mean_k - mean_общ| / mean_общ <= MEAN_TOL
    mean_dev = np.abs(mean_values - overall_mean) / overall_mean
    max_mean_dev = float(mean_dev.max())
    n_out = int((mean_dev > MEAN_TOL).sum())
    mean_ok = max_mean_dev <= MEAN_TOL
    for r, d in zip(rows, mean_dev):
        r["mean_dev_pct"] = 100.0 * float(d)
        r["mean_ok"] = bool(d <= MEAN_TOL)

    # диагностика: равенство средних и дисперсий
    anova_welch = stats.f_oneway(*groups, equal_var=False)
    anova_classic = stats.f_oneway(*groups, equal_var=True)
    leve = stats.levene(*groups, center="median")
    bart = stats.bartlett(*groups)
    homo_mean = anova_welch.pvalue >= 0.05
    homo_var = leve.pvalue >= 0.05
    homo = mean_ok

    print(f"интервалов на участок: min={min_int}, max={max_int}; "
          f"машин на участок: min={min_n}, max={max_n}")
    print(f"допуск на среднее: ±{100 * MEAN_TOL:.0f}% "
          f"от общего среднего")
    print(f"средние участков: min={mean_values.min():.4f}, "
          f"mean={mean_values.mean():.4f}, max={mean_values.max():.4f}; "
          f"общее={overall_mean:.4f}")
    print(f"отклонение средних от общего: max={100 * max_mean_dev:.2f}%, "
          f"вне допуска ±{100 * MEAN_TOL:.0f}%: {n_out} из {N}")
    print(f"критерий средних: "
          f"{'ПРИНЯТ' if mean_ok else 'НЕ ВЫПОЛНЕН'} "
          f"(допуск {100 * MEAN_TOL:.0f}%)")

    print(f"\nдиагностика (на вердикт не влияет):")
    print(f"  Welch ANOVA: F={anova_welch.statistic:.4f}, "
          f"p={anova_welch.pvalue:.4f}")
    print(f"  классическая ANOVA: F={anova_classic.statistic:.4f}, "
          f"p={anova_classic.pvalue:.4f}")
    print(f"  Levene: W={leve.statistic:.4f}, p={leve.pvalue:.4f}")
    print(f"  Bartlett: T={bart.statistic:.4f}, p={bart.pvalue:.4f}")

    print(f"\nВердикт по средним (допуск {100 * MEAN_TOL:.0f}%): "
          f"{'ПРИНИМАЕТСЯ' if mean_ok else 'ОТВЕРГАЕТСЯ'}")
    print(f"  непрерывный прогон "
          f"{'допустим' if mean_ok else 'допустим'}: "
          f"средние {'стабильны' if mean_ok else 'отклоняются более чем на 5%'}")

    # таблица дисперсий по участкам
    seg_path = RESULTS / "lab3_continuous" / "segment_variances.csv"
    with open(seg_path, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["segment", "start", "end",
                     "n_intervals", "n_cars", "mean", "variance",
                     "mean_dev_pct", "mean_within_5"])
        for r in rows:
            wr.writerow([r["segment"], r["start"], r["end"],
                         r["n_intervals"], r["n_cars"],
                         r["mean"], r["var"],
                         r["mean_dev_pct"], int(r["mean_ok"])])
    print(f"средние и дисперсии по участкам: {seg_path}")

    # график: средние и дисперсии по участкам
    fig, (ax_mean, ax_var) = plt.subplots(2, 1, figsize=(10, 7.2),
                                          sharex=True)
    idx = np.array([r["segment"] for r in rows])

    ax_mean.plot(idx, mean_values, "o-", ms=3.5, lw=1.0,
                 label="взвешенное среднее участка")
    ax_mean.axhline(overall_mean, color="red", ls="--", lw=1.2,
                    label=f"общее среднее={overall_mean:.2f}")
    out = mean_dev > MEAN_TOL
    if out.any():
        ax_mean.scatter(idx[out], mean_values[out], color="red",
                        s=28, zorder=5,
                        label=f"вне допуска ±{100 * MEAN_TOL:.0f}%")
    ax_mean.set_ylabel("среднее ожидание, сек")
    ax_mean.set_title(f"п.1.5: {N} участков по {W:.0f} с, "
                      f"допуск ±{100 * MEAN_TOL:.0f}%; "
                      f"max откл.={100 * max_mean_dev:.2f}%, "
                      f"вне допуска: {n_out}")
    ax_mean.legend(fontsize=8); ax_mean.grid(alpha=0.3)

    ax_var.plot(idx, var_values, "o-", ms=3.5, lw=1.0,
                label="взвешенная дисперсия участка")
    ax_var.axhline(overall_var, color="red", ls="--", lw=1.2,
                   label=f"общая дисперсия={overall_var:.2f}")
    ax_var.set_xlabel("номер участка")
    ax_var.set_ylabel("дисперсия ожидания, сек²")
    ax_var.legend(fontsize=8); ax_var.grid(alpha=0.3)

    fig.tight_layout(); fig.savefig(FIGS / "1_5_continuous.png", dpi=120)
    plt.close(fig)

    return dict(t0=T0, t_short=float(t_short), window=W, n_segments=N,
                n=min_n,
                mean_stat=float(anova_welch.statistic),
                mean_p=float(anova_welch.pvalue),
                mean_stat_classic=float(anova_classic.statistic),
                mean_p_classic=float(anova_classic.pvalue),
                levene_stat=float(leve.statistic),
                levene_p=float(leve.pvalue),
                bartlett_stat=float(bart.statistic),
                bartlett_p=float(bart.pvalue),
                mean_min=float(mean_values.min()),
                mean_max=float(mean_values.max()),
                mean_avg=float(mean_values.mean()),
                overall_mean=overall_mean,
                var_min=float(var_values.min()),
                var_max=float(var_values.max()),
                var_mean=float(var_values.mean()),
                overall_var=overall_var,
                mean_tol=MEAN_TOL,
                mean_ok=mean_ok,
                max_mean_dev_pct=100.0 * max_mean_dev,
                n_out_5=n_out,
                homo_mean=homo_mean, homo_var=homo_var,
                homo=homo, rows=rows)

# ---------- 1.6 ----------

def task_1_6(resdir="lab3_sensitivity", fig_name="1_6_sensitivity.png"):
    """Чувствительность и достаточная точность задания входной переменной.
    Данные пишет main.cpp: {resdir}/{variable}_x{k}_summary.csv (k=-3..3),
    x0 берётся из конфига и описывается в {resdir}/meta.csv — анализ
    полностью общий, подходит для любой переменной."""
    meta_path = RESULTS / resdir / "meta.csv"
    with open(meta_path) as fh:
        rd = csv.DictReader(fh)
        meta = next(rd)                       # первая строка — описание опыта
    var = meta["variable"]
    x0 = float(meta["x0"])
    delta = float(meta["delta"])

    print(f"\n=== 1.6 Чувствительность ({var}, x0={x0:g}, δ={delta:g}) ===")
    rows = []
    for k in range(-3, 4):
        path = RESULTS / resdir / f"{var}_x{k}_summary.csv"
        if not path.exists():
            continue
        ys = read_Y(path)
        x = x0 + k * delta
        wl, wh, a = willink_ci(ys)
        rows.append(dict(name=path.stem, k=k, x=x, n=len(ys), mean=ys.mean(),
                         s=ys.std(ddof=1), ymin=ys.min(), ymax=ys.max(),
                         ys=ys, wl=wl, wh=wh, a=a))
    if len(rows) < 3:
        raise RuntimeError(f"{resdir}: недостаточно точек ({len(rows)})")
    rows.sort(key=lambda r: r["k"])
    x0_row = next((r for r in rows if abs(r["x"] - x0) < 1e-9), rows[len(rows)//2])
    x0, y0 = x0_row["x"], x0_row["mean"]
    for r in rows:
        print(f"{var}_x{r['k']:+d} x={r['x']:g}  n={r['n']}  mean={r['mean']:8.4f}  "
              f"s={r['s']:7.4f}  Уиллинк=[{r['wl']:.2f}; {r['wh']:.2f}]")

    d = 0.05 * y0          # «несущественная» погрешность отклика
    print(f"\nY(x0)={y0:.4f} → d (5%) = {d:.4f}")

    # --- критерий из лекции: ВНУТРИ точки (реплик — выборка y) ---
    print("\nразброс внутри точки (max y − min y ≤ d → нет чувствительности):")
    for r in rows:
        spread = r["ymax"] - r["ymin"]
        print(f"x={r['x']:g} spread={spread:7.3f} → "
              f"{'НЕ чувствительна' if spread <= d else 'чувствительна'}")

    # --- разница средних соседних точек ---
    means = np.array([r["mean"] for r in rows])
    spread_means = means.max() - means.min()
    print(f"\nразброс средних точек max(Ybar)-min(Ybar)={spread_means:.4f}")

    print(f"\nt-тесты соседних точек (δ={delta:g}):")
    adj_significant = False
    for i in range(len(rows) - 1):
        ys1, ys2 = rows[i]["ys"], rows[i + 1]["ys"]
        F = max(ys1.std(ddof=1), ys2.std(ddof=1)) ** 2 \
            / min(ys1.std(ddof=1), ys2.std(ddof=1)) ** 2
        F_cr = stats.f.ppf(0.95, len(ys1) - 1, len(ys2) - 1)
        eq = F <= F_cr
        tval, pval = stats.ttest_ind(ys1, ys2, equal_var=eq)
        diff = rows[i + 1]["mean"] - rows[i]["mean"]
        sig = pval < 0.05
        adj_significant |= sig
        print(f"x={rows[i]['x']:g}→{rows[i+1]['x']:g}: "
              f"ΔYbar={diff:7.3f}, {'t' if eq else 'Welch'}={tval:6.3f}, "
              f"p={pval:5.3f} → {'различаются' if sig else 'не различаются'}")

    # --- крайние точки: диапазон варьирования целиком ---
    ys_l, ys_r = rows[0]["ys"], rows[-1]["ys"]
    _, p_ex = stats.ttest_ind(ys_l, ys_r, equal_var=False)
    extremes_significant = bool(p_ex < 0.05)
    print(f"\nкрайние точки x={rows[0]['x']:g} vs {rows[-1]['x']:g}: "
          f"ΔYbar={rows[-1]['mean'] - rows[0]['mean']:.3f}, "
          f"Welch p={p_ex:.4f} → "
          f"{'различаются' if extremes_significant else 'не различаются'}")

    # --- чувствительность dY/dx и достаточная точность задания переменной ---
    # Y(x) может быть нелинейна (насыщение), поэтому:
    # - глобальный наклон по всем точкам — масштаб эффекта;
    # - δ_max = допустимая точность задания переменной — по ЛОКАЛЬНОМУ
    #   наклону в окрестности x0 (точки k=-1, 0, +1)
    xs = np.array([r["x"] for r in rows])
    slope, intercept, r_val, p_slope, se = stats.linregress(xs, means)
    mid_rows = [r for r in rows if -1 <= r["k"] <= 1]
    xs_m = np.array([r["x"] for r in mid_rows])
    means_m = np.array([r["mean"] for r in mid_rows])
    slope_loc, intercept_loc, r_loc, p_loc, _se = stats.linregress(xs_m, means_m)
    if abs(slope_loc) < 1e-12:
        delta_max = math.inf
        delta_max_text = "не ограничена"
    else:
        delta_max = 0.05 * y0 / abs(slope_loc)
        delta_max_text = f"{delta_max:.4f}"
    print(f"\nрегрессия Y({var}): dY/dx={slope:.2f} "
          f"глобально (R²={r_val ** 2:.3f}, p={p_slope:.4f}); "
          f"локально у x0 dY/dx≈{slope_loc:.2f}")
    print(f"достаточная точность задания {var} (локально): "
          f"|Δx| <= {delta_max_text} "
          f"(иначе ΔY выходит за d=5%)")

    sensitive = adj_significant or extremes_significant
    verdict_detail = (
        f"; значимых различий соседних точек на шкале δ={delta:g} "
        f"{'есть' if adj_significant else 'нет'}, различие крайних точек "
        f"{'значимо' if extremes_significant else 'не значимо'}; достаточная "
        f"точность задания переменной δ_max≈{delta_max_text}")
    print(f"\nИТОГ: к {var} модель "
          + ("ЧУВСТВИТЕЛЬНА" if sensitive else "НЕ ЧУВСТВИТЕЛЬНА")
          + verdict_detail)

    # --- график ---
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    n_pp = rows[0]["n"]
    t_cr = stats.t.ppf(0.975, n_pp - 1)
    err = [t_cr * r["s"] / math.sqrt(r["n"]) for r in rows]
    ax.errorbar(xs, means, yerr=err, fmt="o-", capsize=5,
                label=f"Ȳ ± t·s/√n (n={n_pp} на точку)")
    xx = np.linspace(xs.min(), xs.max(), 50)
    ax.plot(xx, intercept + slope * xx, "r--",
            label=f"глобальная регрессия: {slope:.0f}·x{intercept:+.1f}")
    xxm = np.linspace(xs_m.min(), xs_m.max(), 50)
    ax.plot(xxm, intercept_loc + slope_loc * xxm, "g-.",
            label=f"локальная у x0: {slope_loc:.0f}·x{intercept_loc:+.1f}")
    ax.axhspan(y0 - d, y0 + d, color="green", alpha=0.15,
               label=f"полоса ±d=5% ({d:.1f})")
    ax.set_xlabel(f"{var}"); ax.set_ylabel("Ȳ, сек")
    ax.set_title(f"п.1.6: чувствительность к {var}\n"
                 f"dY/dx≈{slope_loc:.0f} (лок.), "
                 f"δ_max({var})≈{delta_max_text}")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / fig_name, dpi=120)
    plt.close(fig)

    return dict(var=var, x0=x0, delta=delta, rows=rows,
                y0=y0, d=d, slope=slope, slope_loc=slope_loc,
                delta_max=delta_max, delta_max_text=delta_max_text,
                sensitive=sensitive, p_slope=p_slope)

# ---------- main ----------

Y0_LABEL = "{Y0}"

# Каталоги и графики п.1.6 — порядок совпадает с sensitivity_cases
# в src/main.cpp. Добавление нового параметра = одна строка здесь.
SENSITIVITY_CASES = (
    ("lab3_sens_passage",   "1_6_sensitivity_passage.png"),
    ("lab3_sens_cinterval", "1_6_sensitivity_cinterval.png"),
    ("lab3_sens_tgreen",    "1_6_sensitivity_tgreen.png"),
    ("lab3_sens_tred",      "1_6_sensitivity_tred.png"),
    ("lab3_sensitivity",    "1_6_sensitivity.png"),
    ("lab3_sens_lambdab",   "1_6_sensitivity_lambdab.png"),
)

def main():
    r11 = task_1_1()
    r12 = task_1_2()
    r13 = task_1_3()
    r14 = task_1_4()
    r14b = task_1_4b()

    # п.1.5: T0=1200, T_short — из п.1.4
    t_short = r14b.get("t_short") if r14b else None
    if t_short is None:
        print("\n1.5: пропуск — T_short из п.1.4 не определён")
        r15 = None
    else:
        r15 = task_1_5(t_short)

    # п.1.6: чувствительность ко всем параметрам модели
    r16 = [task_1_6(resdir, fig_name)
           for resdir, fig_name in SENSITIVITY_CASES]

    # сводка по всем параметрам — в консоль и в CSV
    print("\n=== 1.6 Сводка чувствительности по всем параметрам ===")
    print(f"{'параметр':<16}{'x0':>10}{'δ':>8}{'dY/dx':>12}"
          f"{'δ_max':>12}  вывод")
    for r in r16:
        print(f"{r['var']:<16}{r['x0']:>10.4g}{r['delta']:>8.4g}"
              f"{r['slope_loc']:>12.4g}{r['delta_max_text']:>12}  "
              f"{'чувствительна' if r['sensitive'] else 'не чувствительна'}")

    summary_path = RESULTS / "lab3_sensitivity_summary.csv"
    with open(summary_path, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["variable", "x0", "delta", "y0", "dY_dx_global",
                     "dY_dx_local", "delta_max", "sensitive"])
        for r in r16:
            wr.writerow([
                r["var"], r["x0"], r["delta"], r["y0"],
                r["slope"], r["slope_loc"],
                "inf" if math.isinf(r["delta_max"]) else r["delta_max"],
                int(r["sensitive"]),
            ])
    print(f"сводка сохранена: {summary_path}")

    print("\n=== ИТОГ ===")
    print(f"1.1: нормальность "
          f"{'ПРИНЯТА' if r11['accepted'] else 'ОТВЕРГНУТА'}")
    print(f"1.2: Ȳ={r12['mu']:.3f}; t-ДИ=[{r12['lo']:.3f}; {r12['hi']:.3f}]; "
          f"Уиллинк=[{r12['wl']:.3f}; {r12['wh']:.3f}]")
    print(f"1.3: n*≈{r13['n_star']} (точность 5%)")
    if r14b and r14b.get("t_short") is not None:
        print(f"1.4: T0={T_SETTLE:.0f} (принято), "
              f"T_short={r14b['t_short']} сек, "
              f"окно после T0={r14b['window']:.0f} сек")
    else:
        print(f"1.4: T0={T_SETTLE:.0f} (принято), T_short не найден")
    if r15 is not None:
        print(f"1.5: {r15['n_segments']} участков по {r15['window']:.0f} с: "
              f"max отклонение среднего={r15['max_mean_dev_pct']:.2f}% "
              f"(допуск ±{100 * r15['mean_tol']:.0f}%), "
              f"вне допуска={r15['n_out_5']}/{r15['n_segments']} → "
              f"{'средние стабильны, непрерывный прогон допустим' if r15['mean_ok'] else 'средние отклоняются более чем на 5%, непрерывный прогон недопустим'}; "
              f"диагностика: Welch p={r15['mean_p']:.3f}, "
              f"Levene p={r15['levene_p']:.3f}")
    for r in r16:
        print(f"1.6: {r['var']}: δ_max≈{r['delta_max_text']} → "
              f"{'чувствительна' if r['sensitive'] else 'не чувствительна'}")
    print(f"\nграфики: {FIGS}")


if __name__ == "__main__":
    main()