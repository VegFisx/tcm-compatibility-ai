# -*- coding: utf-8 -*-
r"""
18 组复方 hERG 排序图（论文 Figure 2）
- 按 hERG 降序排列
- 按传统关系配色
- 加 0.5 高风险阈值线
输出: docs/figures/fig6_groups_herg.png
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(r"D:\TCMAI")
FIG_DIR = ROOT / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ---- 读数据 ----
df = pd.read_csv(ROOT / "logs" / "batch_groups.csv")
df = df.dropna(subset=["hERG"]).sort_values("hERG", ascending=True).reset_index(drop=True)
print(f"[info] {len(df)} 组数据")

# ---- 按传统关系配色 ----
def color_of(relation):
    if "十八反" in relation:
        return "#c0392b"      # 红
    if "十九畏" in relation:
        return "#e67e22"      # 橙
    if "相畏" in relation or "减毒" in relation:
        return "#8e44ad"      # 紫
    if "相须" in relation or "相使" in relation:
        return "#2980b9"      # 蓝
    return "#27ae60"          # 绿（复方）

colors = [color_of(r) for r in df["传统关系"]]

# ---- 图 ----
fig, ax = plt.subplots(figsize=(13, 9), dpi=200)

y_pos = range(len(df))
bars = ax.barh(y_pos, df["hERG"], color=colors,
               edgecolor="black", linewidth=0.8, height=0.72)

# y 轴标签：复方名 + 药味数
labels = [f"{row['复方']}  ({int(row['药味数'])}味)"
          for _, row in df.iterrows()]
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=11)

# x 轴
ax.set_xlabel("hERG 阻断概率（均值）", fontsize=13)
ax.set_xlim(0, 0.65)
ax.axvline(0.5, color="gray", linestyle="--", linewidth=1.2,
           label="高风险阈值 (0.5)")
ax.grid(axis="x", linestyle=":", alpha=0.5)

# 柱顶数值
for bar, v in zip(bars, df["hERG"]):
    ax.text(v + 0.005, bar.get_y() + bar.get_height() / 2,
            f"{v:.3f}", va="center", fontsize=10, fontweight="bold")

# 图例（自定）
from matplotlib.patches import Patch
legend_items = [
    Patch(facecolor="#c0392b", edgecolor="black", label="十八反"),
    Patch(facecolor="#e67e22", edgecolor="black", label="十九畏"),
    Patch(facecolor="#8e44ad", edgecolor="black", label="相畏/减毒"),
    Patch(facecolor="#2980b9", edgecolor="black", label="相须/相使"),
    Patch(facecolor="#27ae60", edgecolor="black", label="经典复方"),
]
ax.legend(handles=legend_items, loc="lower right",
          fontsize=10, framealpha=0.95, title="传统关系", title_fontsize=11)

# 标题
ax.set_title("18 组中药配伍/复方的 hERG 毒性预测（按均值排序）",
             fontsize=15, fontweight="bold", pad=15)

plt.tight_layout()
out = FIG_DIR / "fig6_groups_herg.png"
plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
plt.close()
print(f"[ok] {out}")