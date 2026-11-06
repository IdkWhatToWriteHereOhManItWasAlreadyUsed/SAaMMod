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
    print("\n=== 1.1 Хи-квадрат на нормальность (n=180) ===")
    ys = read_Y(RESULTS / "lab3_base_n180_summary.csv")
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
    print("\n=== 1.4 Переходный период ===")
    data = read_intervals(RESULTS / "lab3_transient/transient_interval.csv")
    reps = sorted(data)
    print(f"реплик: {len(reps)}")

    t = data[reps[0]][0]
    Y_int = np.vstack([data[r][1] for r in reps])   # NaN — пустой интервал
    Y_cum = np.vstack([data[r][2] for r in reps])
    W_cnt = np.vstack([data[r][3] for r in reps])   # число машин в интервале
    print(f"пустых интервалов (NA): {int(np.isnan(Y_int).sum())} из {Y_int.size}")

    W = 600          # окно сравнения/сглаживания, сек
    HALF_W = 300     # полуширина сглаживания, сек

    # взвешенные по числу машин средние — согласованы с семантикой Y
    # (интервалы с 1 машиной не весят так же, как интервалы с 5 машинами)
    def wmean(rep, tt0, tt1):
        yi, wc = data[rep][1], data[rep][3]
        m = (t >= tt0) & (t < tt1) & ~np.isnan(yi)
        c = wc[m]
        return float(np.sum(yi[m] * c) / c.sum()) if c.sum() > 0 else np.nan

    def rolling_weighted(rep, half):
        # центрированное скользящее взвешенное среднее, окно 2*half
        out = np.full(len(t), np.nan)
        for i, ti in enumerate(t):
            v = wmean(rep, ti - half, ti + half)
            out[i] = v
        return out

    # --- тесты стационарности: ПО ИНТЕРВАЛ-ЗНАЧЕНИЯМ, не по кумулятиву ---
    # окно [T,T+W) против [T+W,T+2W), среднее взвешено числом машин,
    # парный t-тест по репликам
    print(f"\nвзвешенные средние окна [T,T+W) vs [T+W,T+2W), W={W}:")
    print(f"{'T':>6} {'mean1':>8} {'mean2':>8} {'p(парный t)':>12} "
          f"{'стационарно (p>=0.05)':>22}")
    first_stationary = None
    rows_stat = []
    for T in range(200, int(t[-1]) - 2 * W + 1, 200):
        m1 = np.array([wmean(r, T, T + W) for r in reps])
        m2 = np.array([wmean(r, T + W, T + 2 * W) for r in reps])
        ok = ~np.isnan(m1) & ~np.isnan(m2)
        if ok.sum() < 5:
            continue
        tval, pval = stats.ttest_rel(m1[ok], m2[ok])
        stat = pval >= 0.05
        rows_stat.append((T, pval))
        if stat and first_stationary is None:
            first_stationary = T
        print(f"{T:6d} {m1[ok].mean():8.3f} {m2[ok].mean():8.3f} "
              f"{pval:12.3f} {'да' if stat else '—':>22}")

    # --- автоматический T_пер: сравнение уровней «префикс vs хвост» ---
    # для границы ti: взвешенное среднее ожидания по [0,ti) против [ti,t_end),
    # парный t-тест по репликам (каждая реплика — блок). T_пер — первая
    # граница, начиная с которой H0 не отвергается и для двух границ подряд
    pairs = []
    for ti in range(W, int(t[-1]) - W + 1, W):
        pre = np.array([wmean(r, 0, ti) for r in reps])
        post = np.array([wmean(r, ti, t[-1]) for r in reps])
        ok = ~np.isnan(pre) & ~np.isnan(post)
        if ok.sum() < 5:
            continue
        _, p = stats.ttest_rel(pre[ok], post[ok])
        pairs.append((int(ti), float(pre[ok].mean()), float(post[ok].mean()), p))
    print(f"\nпрефикс [0,T) vs хвост [T,{t[-1]:.0f}): парный тест по репликам")
    print(f"{'T':>6} {'до T':>8} {'после T':>8} {'p':>7} {'стационарно':>12}")
    T_detect = None
    LOOK_AHEAD = 2   # устойчивость: принято и для двух границ подряд
    for k, (ti, m_pre, m_post, p) in enumerate(pairs):
        stable = all(q >= 0.05 for *_, q in pairs[k:k + LOOK_AHEAD + 1])
        print(f"{ti:6d} {m_pre:8.3f} {m_post:8.3f} {p:7.3f} "
              f"{'да' if stable else '—':>12}")
        if stable and T_detect is None:
            T_detect = ti
    steady_level = (np.nanmean([wmean(r, (T_detect or 0) + W,
                                (T_detect or 0) + 2 * W) for r in reps])
                    if T_detect else np.nan)
    if T_detect is None:
        print(f"\nT_пер не найден — см. таблицу выше")
    else:
        print(f"\nT_пер ≈ {T_detect} сек, уровень отклика после T_пер "
              f"≈ {steady_level:.1f} сек")

    # --- график: сглаженные взвешенные кривые по репликам + их среднее ---
    curves = np.array([rolling_weighted(r, HALF_W) for r in reps])
    curve_mean = np.nanmean(np.where(np.isnan(curves), np.nan, curves), axis=0)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, r in enumerate(reps):
        ax.plot(t, curves[i], lw=0.7, alpha=0.35)
    ax.plot(t, curve_mean, "b-", lw=2.2,
            label="Y_interval (взвеш. по числу машин), среднее по репликам")
    ax.plot(t, smooth(t, Y_cum.mean(axis=0), HALF_W), "k--", lw=1.5,
            label="Y_cum кумулятив (визуализация)")
    if T_detect is not None:
        ax.axvline(T_detect, color="red", ls="--", lw=1.2,
                   label=f"T_пер ≈ {T_detect:.0f} сек")
    else:
        ax.text(0.02, 0.02, "T_пер критерием не найден", transform=ax.transAxes,
                fontsize=8, color="red")
    ax.set_xlabel("модельное время, сек")
    ax.set_ylabel("среднее ожидание, сек")
    ax.set_title(f"п.1.4: взвешенные Y_interval (окно {2*HALF_W} с) "
                 f"и кумулятив, 10 реплик")
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "1_4_transient.png", dpi=120)
    plt.close(fig)

    return dict(T_detect=T_detect, first_stationary=first_stationary,
                rows_stat=tuple(rows_stat), steady_level=steady_level)

# ---------- 1.4b: гипотеза об уменьшении времени прогона ----------

def task_1_4b():
    print("\n=== 1.4b Однородность {Y0}(T0=6000) и {YT}: "
          "можно ли сократить прогон? ===")
    ref = read_Y(RESULTS / "lab3_shortened/T6000_summary.csv")
    n0 = len(ref)
    mu0, s0 = ref.mean(), ref.std(ddof=1)
    print(f"эталон {Y0_LABEL}: T1=6000, n={n0}, mean={mu0:.4f}, s={s0:.4f}")

    rows = []
    for path in sorted((RESULTS / "lab3_shortened").glob("T*_summary.csv")):
        Ti = int(path.stem.replace("_summary", "")[1:])
        if Ti == 6000:
            continue
        ys = read_Y(path)
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
        rows.append(dict(T=Ti, mu=muT, s=sT, F=F, F_cr=F_cr,
                         var_equal=var_equal, test=test, t=tval,
                         p=pval, homo=homo))
        print(f"T={Ti:5d}  mean={muT:8.4f} s={sT:7.4f} | "
              f"F={F:5.3f} (кр={F_cr:5.3f} → "
              f"{'дисперсии равны' if var_equal else 'дисперсии РАЗНЫЕ'}) | "
              f"{test}: t={tval:6.3f} p={pval:5.3f} → "
              f"{'ОДНОРОДНЫ' if homo else 'различаются'}")

    rows.sort(key=lambda r: r["T"])
    # Т0 — эталонная реплика; Т1 — максимальное Т<Т0, однородное целиком
    # (равенство дисперсий И средних); Т2 — минимальное Т, при котором ещё
    # не отвергается равенство средних
    t1 = max((r["T"] for r in rows if r["var_equal"] and r["homo"]), default=None)
    t2 = min((r["T"] for r in rows if r["homo"]), default=None)
    if t1 is not None:
        print(f"\nТ1={6000} (эталон {Y0_LABEL}); Т1={t1} (однородность по "
              f"дисперсиям и средним); Т2={t2} (минимум, где среднее ещё "
              f"не смещено)")
        print(f"вывод: реплику можно сократить с 6000 до {t1} сек; "
              f"ниже {t2} сек среднее занижено, уменьшение недопустимо")
    else:
        print(f"\nоднородных точек нет — время реплики сокращать нельзя")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ts_ = [r["T"] for r in rows]
    ms_ = [r["mu"] for r in rows]
    err_ = []
    for r in rows:
        path = RESULTS / f"lab3_shortened/T{r['T']}_summary.csv"
        ys = read_Y(path)
        err_.append(stats.t.ppf(0.975, len(ys) - 1) * r["s"] / math.sqrt(len(ys)))
    ref_err = stats.t.ppf(0.975, n0 - 1) * s0 / math.sqrt(n0)
    ax.errorbar(ts_, ms_, yerr=err_, fmt="o-", capsize=4,
                label="{YT}, n=30")
    ax.errorbar([6000], [mu0], yerr=ref_err, fmt="s", capsize=4,
                color="red", label="{Y0} (T1=6000, эталон)")
    ax.axhline(mu0, color="gray", ls=":")
    if t1:
        ax.axvline(t1, color="green", ls=":", alpha=0.8,
                   label=f"Т1={t1} (однороден целиком)")
    if t2 and t2 != t1:
        ax.axvline(t2, color="orange", ls="--", alpha=0.8,
                   label=f"Т2={t2} (граница смещения среднего)")
    ax.set_xlabel("T окончания реплики, сек"); ax.set_ylabel("Ȳ, сек")
    ax.set_title("п.1.4b: однородность выборок при сокращении прогона")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "1_4b_shortened.png", dpi=120)
    plt.close(fig)

    return dict(t0=6000, t1=t1, t2=t2, rows=rows)


def task_1_5(t0=None, t2=None):
    """П.1.5: контрольная выборка A=[T0,T2) и B=[T2, 2T2-T0).
    F-тест дисперсий + t-тест средних. Если однородны — соседние
    отрезки дают одинаковый Y, «шва» между кусками нет, непрерывный
    прогон допустим."""
    if t0 is None:
        raise RuntimeError("task_1_5: нужен T0 из task_1_4")
    if t2 is None:
        raise RuntimeError("task_1_5: нужен T2 из task_1_4b")

    T0 = int(t0)
    T2 = int(t2)
    L  = T2 - T0                # длина отрезка A
    T3 = T2 + L                 # конец отрезка B

    print(f"\n=== 1.5 Непрерывный прогон: A=[T0,T2) vs B=[T2,T3) ===")
    print(f"T0={T0}, T2={T2}, T3={T3} (длина отрезка {L} сек)")

    path = RESULTS / "lab3_continuous/continuous_interval.csv"
    if not path.exists():
        print(f"п.1.5: нет {path} — пропуск")
        return None
    data = read_intervals(path)
    reps = sorted(data)
    print(f"реплик: {len(reps)}")

    t_max = max(float(data[r][0][-1]) for r in reps)
    if T3 > t_max:
        print(f"п.1.5: T3={T3} > T_max={t_max:.0f}, "
              f"сокращаю B вдвое (до {T2 + L // 2})")
        T3 = T2 + L // 2
        if T3 <= T2:
            print("п.1.5: B вырожден — пропуск")
            return None

    def y_window(rep, a, b):
        t, yi, _yc, wc = data[rep]
        m = (t >= a) & (t < b) & ~np.isnan(yi)
        w = wc[m]
        return float(np.sum(yi[m] * w) / w.sum()) if w.sum() > 0 else np.nan

    A = np.array([y_window(r, T0, T2) for r in reps])
    B = np.array([y_window(r, T2, T3) for r in reps])
    ok = ~np.isnan(A) & ~np.isnan(B)
    A, B = A[ok], B[ok]
    nA, nB = len(A), len(B)
    print(f"A=[{T0},{T2}): n={nA}  mean={A.mean():.4f}  s={A.std(ddof=1):.4f}")
    print(f"B=[{T2},{T3}): n={nB}  mean={B.mean():.4f}  s={B.std(ddof=1):.4f}")

    # F-тест дисперсий
    vA, vB = A.var(ddof=1), B.var(ddof=1)
    F = max(vA, vB) / min(vA, vB)
    v1, v2 = ((nA - 1, nB - 1) if vA >= vB else (nB - 1, nA - 1))
    F_cr = stats.f.ppf(0.95, v1, v2)
    var_equal = F <= F_cr

    # t-тест средних
    if var_equal:
        sv = ((nA - 1) * vA + (nB - 1) * vB) / (nA + nB - 2)
        t_val = (A.mean() - B.mean()) / math.sqrt(sv * (1 / nA + 1 / nB))
        dof = nA + nB - 2
        p_val = 2 * (1 - stats.t.cdf(abs(t_val), dof))
        test = "t"
    else:
        t_val, p_val = stats.ttest_ind(A, B, equal_var=False)
        test = "Welch"

    print(f"F = {F:.4f}, F_кр(0.95,{v1},{v2}) = {F_cr:.4f} → "
          f"дисперсии {'равны' if var_equal else 'РАЗНЫЕ'}")
    print(f"{test}: t = {t_val:.4f}, p = {p_val:.4f} → "
          f"средние {'равны' if p_val >= 0.05 else 'РАЗНЫЕ'}")

    homo = var_equal and (p_val >= 0.05)
    print(f"\nГипотеза о возможности непрерывного прогона: "
          f"{'ПРИНИМАЕТСЯ' if homo else 'ОТВЕРГАЕТСЯ'}")
    print(f"  (соседние отрезки [{T0},{T2}) и [{T2},{T3}) "
          f"{'не различаются' if homo else 'различаются'} по Y)")

    # график
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(A, bins=10, alpha=0.5, edgecolor="black",
            label=f"A: [{T0},{T2}), n={nA}")
    ax.hist(B, bins=10, alpha=0.5, edgecolor="black",
            label=f"B: [{T2},{T3}), n={nB}")
    ax.axvline(A.mean(), color="C0", ls="--", label=f"mean A={A.mean():.2f}")
    ax.axvline(B.mean(), color="C1", ls="--", label=f"mean B={B.mean():.2f}")
    ax.set_xlabel("Y по отрезку, сек"); ax.set_ylabel("частота")
    ax.set_title(f"п.1.5: A=[{T0},{T2}), B=[{T2},{T3}); "
                 f"F={F:.2f}, p(t)={p_val:.3f}")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / "1_5_continuous.png", dpi=120)
    plt.close(fig)

    return dict(t0=T0, t2=T2, t3=T3, n=nA,
                mean_A=A.mean(), mean_B=B.mean(),
                F=F, F_cr=F_cr, var_equal=var_equal,
                t=t_val, p=p_val, homo=homo)

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
    delta_max = 0.05 * y0 / abs(slope_loc)
    print(f"\nрегрессия Y({var}): dY/dx={slope:.2f} "
          f"глобально (R²={r_val ** 2:.3f}, p={p_slope:.4f}); "
          f"локально у x0 dY/dx≈{slope_loc:.2f}")
    print(f"достаточная точность задания {var} (локально): |Δx| <= {delta_max:.4f} "
          f"(иначе ΔY выходит за d=5%)")

    sensitive = adj_significant or extremes_significant
    verdict_detail = (
        f"; значимых различий соседних точек на шкале δ={delta:g} "
        f"{'есть' if adj_significant else 'нет'}, различие крайних точек "
        f"{'значимо' if extremes_significant else 'не значимо'}; достаточная "
        f"точность задания переменной δ_max≈{delta_max:.4f}")
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
                 f"dY/dx≈{slope_loc:.0f} (лок.), δ_max({var})≈{delta_max:.4f}")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIGS / fig_name, dpi=120)
    plt.close(fig)

    return dict(var=var, rows=rows, y0=y0, d=d, slope=slope,
                slope_loc=slope_loc, delta_max=delta_max,
                sensitive=sensitive, p_slope=p_slope)

# ---------- main ----------

Y0_LABEL = "{Y0}"

def main():
    r11 = task_1_1()
    r12 = task_1_2()
    r13 = task_1_3()
    r14 = task_1_4()
    r14b = task_1_4b()

    # п.1.5: T0 — из 1.4, T2 — из 1.4b (сокращение)
    t0_est = r14.get("T_detect")
    t2_cut = r14b.get("t1") if r14b else None
    if t0_est is None or t2_cut is None:
        print("\n1.5: пропуск — T0/T2 не определены "
              f"(T0={t0_est}, T2={t2_cut})")
        r15 = None
    else:
        r15 = task_1_5(t0_est, t2_cut)

    r16_lambda = task_1_6("lab3_sensitivity", "1_6_sensitivity.png")
    r16_tgreen = task_1_6("lab3_sens_tgreen", "1_6_sensitivity_tgreen.png")

    print("\n=== ИТОГ ===")
    print(f"1.1: нормальность "
          f"{'ПРИНЯТА' if r11['accepted'] else 'ОТВЕРГНУТА'}")
    print(f"1.2: Ȳ={r12['mu']:.3f}; t-ДИ=[{r12['lo']:.3f}; {r12['hi']:.3f}]; "
          f"Уиллинк=[{r12['wl']:.3f}; {r12['wh']:.3f}]")
    print(f"1.3: n*≈{r13['n_star']} (точность 5%)")
    tper = (f"{r14['T_detect']:.0f}"
            if r14['T_detect'] is not None else "?")
    print(f"1.4: T0≈{tper} сек (установление)")
    if r14b:
        print(f"1.4b: T1={6000} (эталон), T2={r14b['t1']} (сокращение)")
    if r15 is not None:
        print(f"1.5: непрерывный прогон "
              f"{'ДОПУСТИМ' if r15['homo'] else 'НЕ ДОПУСТИМ'} "
              f"(F={r15['F']:.2f}, p(t)={r15['p']:.3f}, n={r15['n']})")
    for r16 in (r16_lambda, r16_tgreen):
        print(f"1.6: {r16['var']}: δ_max≈{r16['delta_max']:.4f} → "
              f"{'чувствительна' if r16['sensitive'] else 'не чувствительна'}")
    print(f"\nграфики: {FIGS}")


if __name__ == "__main__":
    main()