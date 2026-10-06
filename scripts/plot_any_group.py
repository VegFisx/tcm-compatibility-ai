# -*- coding: utf-8 -*-
r"""
任意复方的成分 vs 产物 hERG 对比图
用法:
  python plot_any_group.py 四逆汤
  python plot_any_group.py 附子+甘草
  python plot_any_group.py --list    # 列出所有可用的复方
"""
import sys
import argparse
from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from batch_pairs import GROUPS, _collect_compounds
from tcm_analyzer import predict_reactions
from admet_cache import ADMETCache

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

FIG_DIR = ROOT / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def find_group(name):
    for g in GROUPS:
        if g["name"] == name:
            return g
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("group_name", nargs="?", help="复方名，如 四逆汤")
    parser.add_argument("--list", action="store_true", help="列出所有复方")
    args = parser.parse_args()

    if args.list:
        print("可用复方：")
        for g in GROUPS:
            print(f"  {g['name']:14s}  ({len(g['herbs'])}味, {g['relation']})")
        return

    if not args.group_name:
        print("请指定复方名，或 --list 查看全部")
        return

    group = find_group(args.group_name)
    if group is None:
        print(f"[ERR] 找不到 '{args.group_name}'")
        print("可用复方用 --list 查")
        return

    print(f"分析: {group['name']} ({group['relation']}, {len(group['herbs'])}味)")
    cache = ADMETCache()

    # 成分
    compounds = _collect_compounds(group["herbs"])
    print(f"  成分: {len(compounds)}")

    # 成分 hERG
    src_hergs = []
    src_data = []   # (name, herg)
    for c in compounds:
        rec = cache.get(c["smiles"])
        if rec and rec.get("hERG") is not None:
            h = float(rec["hERG"])
            src_hergs.append(h)
            src_data.append((c["name"], h))
    src_data.sort(key=lambda x: -x[1])

    # 产物
    products = predict_reactions(compounds)
    print(f"  产物: {len(products)}")

    # 产物 hERG（按来源分子聚合）
    prod_by_src = {}
    for p in products:
        rec = cache.get(p["smiles"])
        if not rec or rec.get("hERG") is None:
            continue
        prod_by_src.setdefault(p["from_compound"], []).append(float(rec["hERG"]))

    # ---- 图：上下两栏 ----
    fig = plt.figure(figsize=(16, 11), dpi=200, facecolor="white")

    # 顶部标题
    fig.text(0.5, 0.965,
             f"{group['name']}  ({group['relation']}, {len(group['herbs'])}味)",
             ha="center", fontsize=17, fontweight="bold")
    fig.text(0.5, 0.935,
             f"成分 {len(compounds)} | 产物 {len(products)} | "
             f"成分 hERG 均值 {sum(src_hergs) / len(src_hergs):.3f}" if src_hergs else "",
             ha="center", fontsize=11, color="#555555")

    # ---- 左上：成分 hERG Top 20 ----
    ax1 = fig.add_axes([0.06, 0.55, 0.42, 0.35])
    top = src_data[:20]
    names = [n[:20] for n, _ in top][::-1]
    vals = [v for _, v in top][::-1]
    colors1 = ["#d62728" if v > 0.5 else "#2ca02c" for v in vals]
    ax1.barh(range(len(names)), vals, color=colors1, edgecolor="black", linewidth=0.6)
    ax1.set_yticks(range(len(names)))
    ax1.set_yticklabels(names, fontsize=9)
    ax1.axvline(0.5, color="gray", linestyle="--", linewidth=1)
    ax1.set_xlim(0, 1.0)
    ax1.set_xlabel("hERG 概率", fontsize=10)
    ax1.set_title(f"成分 hERG Top 20", fontsize=12, fontweight="bold")
    ax1.grid(axis="x", linestyle=":", alpha=0.4)

    # ---- 右上：产物 hERG Top 20（按来源分子聚合）----
    ax2 = fig.add_axes([0.55, 0.55, 0.42, 0.35])
    # 算每个来源分子的产物 hERG 均值
    prod_avg = [(src, sum(vs) / len(vs), len(vs))
                for src, vs in prod_by_src.items() if len(vs) >= 1]
    prod_avg.sort(key=lambda x: -x[1])
    top_prod = prod_avg[:20]
    names2 = [f"{n[:15]} ({c})" for n, _, c in top_prod][::-1]
    vals2 = [v for _, v, _ in top_prod][::-1]
    colors2 = ["#d62728" if v > 0.5 else "#2ca02c" for v in vals2]
    ax2.barh(range(len(names2)), vals2, color=colors2, edgecolor="black", linewidth=0.6)
    ax2.set_yticks(range(len(names2)))
    ax2.set_yticklabels(names2, fontsize=9)
    ax2.axvline(0.5, color="gray", linestyle="--", linewidth=1)
    ax2.set_xlim(0, 1.0)
    ax2.set_xlabel("hERG 概率（产物均值）", fontsize=10)
    ax2.set_title("产物 hERG Top 20（按来源分子）", fontsize=12, fontweight="bold")
    ax2.grid(axis="x", linestyle=":", alpha=0.4)

    # ---- 下方：hERG 分布直方图 ----
    ax3 = fig.add_axes([0.08, 0.08, 0.84, 0.35])

    # 收集所有产物的 hERG
    prod_hergs_all = []
    for vs in prod_by_src.values():
        prod_hergs_all.extend(vs)

    bins = [i / 20 for i in range(21)]  # 0.00 ~ 1.00，间隔 0.05
    ax3.hist(src_hergs, bins=bins, alpha=0.65, label=f"成分 (n={len(src_hergs)})",
             color="#2980b9", edgecolor="black")
    ax3.hist(prod_hergs_all, bins=bins, alpha=0.55,
             label=f"产物 (n={len(prod_hergs_all)})",
             color="#e67e22", edgecolor="black")
    ax3.axvline(0.5, color="red", linestyle="--", linewidth=1.5,
                label="高风险阈值 (0.5)")
    ax3.axvline(sum(src_hergs) / len(src_hergs) if src_hergs else 0,
                color="#2980b9", linestyle="-", linewidth=1.5,
                label=f"成分均值 {sum(src_hergs) / len(src_hergs):.3f}"
                if src_hergs else "")
    if prod_hergs_all:
        ax3.axvline(sum(prod_hergs_all) / len(prod_hergs_all),
                    color="#e67e22", linestyle="-", linewidth=1.5,
                    label=f"产物均值 {sum(prod_hergs_all) / len(prod_hergs_all):.3f}")
    ax3.set_xlabel("hERG 阻断概率", fontsize=11)
    ax3.set_ylabel("分子数", fontsize=11)
    ax3.set_title("成分 vs 产物 hERG 分布", fontsize=12, fontweight="bold")
    ax3.legend(fontsize=10, loc="upper right")
    ax3.grid(axis="y", linestyle=":", alpha=0.4)

    # 保存
    safe_name = group["name"].replace("+", "_").replace("/", "_")
    out = FIG_DIR / f"fig_group_{safe_name}.png"
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[ok] {out}")


if __name__ == "__main__":
    main()