# -*- coding: utf-8 -*-
r"""
附子煎煮减毒机制图（论文 Figure 级）
- 三个核心分子：Aconitine → Benzoylaconine → Aconine
- 结构 + 反应箭头 + hERG 定量柱状图
- 输出: docs/figures/fig5_detox_pathway.png
"""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Draw

RDLogger.DisableLog('rdApp.*')

ROOT = Path(r"D:\TCMAI")
FIG_DIR = ROOT / "docs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# 中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 三个核心分子
# ============================================================
DATA = [
    {
        "en": "Aconitine",
        "cn": "乌头碱",
        "type": "双酯型",
        "type_en": "Diester",
        "smiles": ("CCN1CC2(C(CC(C34C2C(C(C31)C5(C6C4CC(C6OC(=O)C7=CC=CC=C7)"
                   "(C(C5O)OC)O)OC(=O)C)OC)OC)O)COC"),
        "herg": 0.614,
        "mw": 645.7,
        "color": "#c0392b",
    },
    {
        "en": "Benzoylaconine",
        "cn": "苯甲酰乌头原碱",
        "type": "单酯型",
        "type_en": "Monoester",
        "smiles": ("CCN1CC2(COC)C(O)CC(OC)C34C5CC6(O)C(OC)C(O)C(O)"
                   "(C5C6OC(=O)c5ccccc5)C(C(OC)C23)C14"),
        "herg": 0.533,
        "mw": 603.7,
        "color": "#e67e22",
    },
    {
        "en": "Aconine",
        "cn": "乌头原碱",
        "type": "醇胺型",
        "type_en": "Alkamine",
        "smiles": ("CCN1CC2(COC)C(O)CC(OC)C34C5CC6(O)C(O)C5C(O)"
                   "(C(O)C6OC)C(C(OC)C23)C14"),
        "herg": 0.200,
        "mw": 499.6,
        "color": "#27ae60",
    },
]


# ============================================================
# 分子 2D 渲染
# ============================================================
def mol_image(smiles, size=(600, 600)):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        print(f"[ERR] SMILES 解析失败: {smiles[:60]}")
        return None
    AllChem.Compute2DCoords(mol)
    return np.array(Draw.MolToImage(mol, size=size))


# ============================================================
# 绘图
# ============================================================
fig = plt.figure(figsize=(15, 9.2), dpi=200, facecolor="white")

# ---- 主标题 ----
fig.text(0.5, 0.975,
         "附子煎煮减毒机制：乌头碱类水解路径与 hERG 毒性下降",
         ha="center", va="top", fontsize=18, fontweight="bold")
fig.text(0.5, 0.935,
         "Aconitine  →  Benzoylaconine  →  Aconine   "
         "(Aconitum carmichaelii Debx.)",
         ha="center", va="top", fontsize=11,
         color="#555555", style="italic")

# ---- 三个结构框 ----
x_positions = [0.03, 0.375, 0.72]
box_w = 0.25
box_y = 0.44
box_h = 0.42

for d, x in zip(DATA, x_positions):
    ax = fig.add_axes([x, box_y, box_w, box_h])
    arr = mol_image(d["smiles"])
    if arr is not None:
        ax.imshow(arr, aspect="equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor(d["color"])
        sp.set_linewidth(3)

    cx = x + box_w / 2
    # 英文名
    fig.text(cx, box_y - 0.015, d["en"],
             ha="center", va="top", fontsize=14, fontweight="bold",
             color=d["color"])
    # 中文名
    fig.text(cx, box_y - 0.058, d["cn"],
             ha="center", va="top", fontsize=12, color="#222222")
    # 类型 + 分子量
    fig.text(cx, box_y - 0.098,
             f"{d['type']} ({d['type_en']})   MW = {d['mw']}",
             ha="center", va="top", fontsize=9.5, color="#666666")

# ---- 反应箭头 ----
for i in range(2):
    x1 = x_positions[i] + box_w
    x2 = x_positions[i + 1]
    y = box_y + box_h / 2
    arrow = FancyArrowPatch(
        (x1 + 0.005, y), (x2 - 0.005, y),
        arrowstyle="-|>", mutation_scale=28,
        linewidth=2.5, color="#333333"
    )
    fig.add_artist(arrow)
    cx_arrow = (x1 + x2) / 2

    fig.text(cx_arrow, y + 0.055, "酯水解",
             ha="center", va="bottom", fontsize=12, fontweight="bold")
    fig.text(cx_arrow, y + 0.020,
             "脱乙酰基" if i == 0 else "脱苯甲酰基",
             ha="center", va="bottom", fontsize=9.5,
             color="#555555", style="italic")

    # ΔMW 数值
    delta_mw = DATA[i + 1]["mw"] - DATA[i]["mw"]
    fig.text(cx_arrow, y - 0.045,
             f"ΔMW = {delta_mw:+.0f}",
             ha="center", va="top", fontsize=9, color="#777777")

# ---- hERG 柱状图（上移，避免和底部结论重叠）----
ax_bar = fig.add_axes([0.09, 0.10, 0.82, 0.20])
names = [d["en"] for d in DATA]        # 只留英文，避免和结构图标签重复
values = [d["herg"] for d in DATA]
colors = [d["color"] for d in DATA]

bars = ax_bar.bar(names, values, color=colors, width=0.45,
                  edgecolor="black", linewidth=1.0)
ax_bar.set_ylim(0, 0.85)
ax_bar.set_ylabel("hERG 阻断概率", fontsize=12)
ax_bar.axhline(0.5, color="gray", linestyle="--",
               linewidth=1, label="高风险阈值 (0.5)")
ax_bar.tick_params(axis="x", labelsize=12)
ax_bar.legend(loc="upper right", fontsize=10, framealpha=0.9)
ax_bar.grid(axis="y", linestyle=":", alpha=0.5)

for bar, v in zip(bars, values):
    ax_bar.text(bar.get_x() + bar.get_width() / 2, v + 0.02,
                f"{v:.3f}", ha="center", va="bottom",
                fontsize=14, fontweight="bold", color="#222222",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor="white",
                          edgecolor=bar.get_edgecolor(),
                          linewidth=1))

# ---- 底部结论（下移，加蓝色加粗）----
drop_total = (1 - values[2] / values[0]) * 100
fig.text(0.5, 0.008,
         f"结论：双酯型 → 单酯型 → 醇胺型   |   "
         f"hERG 从 {values[0]:.3f} 降至 {values[2]:.3f}（降低 {drop_total:.0f}%）",
         ha="center", va="bottom", fontsize=13,
         fontweight="bold", color="#0d47a1")

# ---- 保存 ----
out = FIG_DIR / "fig5_detox_pathway.png"
plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
plt.close()
print(f"[ok] {out}")