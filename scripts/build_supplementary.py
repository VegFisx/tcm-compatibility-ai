# -*- coding: utf-8 -*-
r"""
生成补充材料：
- TableS1_reaction_rules.csv   （23 条规则 SMARTS）
- TableS2_batch_results.csv    （18 组完整数据）
- TableS3_product_admet.csv    （10 配伍产物 ADMET）
- FigureS1_architecture.png    （系统架构图）

输出目录：D:\TCMAI\docs\supplementary\
"""
import sys
import csv
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from tcm_analyzer import REACTIONS

OUT = ROOT / "docs" / "supplementary"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


# ============================================================
# Table S1：23 条反应规则
# ============================================================
def build_table_s1():
    out = OUT / "TableS1_reaction_rules.csv"
    rows = []
    for key, rule in REACTIONS.items():
        rows.append({
            "规则名": rule["name"],
            "SMARTS": rule["smarts"].replace("\n", "").replace("  ", ""),
            "不可逆": "是" if rule.get("irreversible", False) else "否",
            "说明": rule.get("desc", ""),
        })
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["规则名", "SMARTS", "不可逆", "说明"])
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] {out.name}  ({len(rows)} 条规则)")


# ============================================================
# Table S2：18 组完整数据
# ============================================================
def build_table_s2():
    src = ROOT / "logs" / "batch_groups.csv"
    out = OUT / "TableS2_batch_results.csv"
    if not src.exists():
        print(f"[跳过] {src} 不存在，先跑 batch_pairs.py")
        return
    with src.open("r", encoding="utf-8-sig") as f:
        content = f.read()
    out.write_text(content, encoding="utf-8-sig")
    n = len(content.strip().splitlines()) - 1
    print(f"[OK] {out.name}  ({n} 行)")


# ============================================================
# Table S3：10 配伍产物 ADMET
# ============================================================
def build_table_s3():
    src = ROOT / "docs" / "reports" / "admet_products_all_summary.csv"
    out = OUT / "TableS3_product_admet.csv"
    if not src.exists():
        print(f"[跳过] {src} 不存在，先跑 run_admet_products_all.py")
        return
    with src.open("r", encoding="utf-8-sig") as f:
        content = f.read()
    out.write_text(content, encoding="utf-8-sig")
    n = len(content.strip().splitlines()) - 1
    print(f"[OK] {out.name}  ({n} 行)")


# ============================================================
# Figure S1：系统架构图
# ============================================================
def build_figure_s1():
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis("off")

    # 颜色
    c_data = "#dbeafe"
    c_calc = "#dcfce7"
    c_out = "#fef3c7"
    c_border = "#94a3b8"

    def box(x, y, w, h, text, color, fontsize=10, bold=False):
        p = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.1",
                           facecolor=color, edgecolor=c_border,
                           linewidth=1.2)
        ax.add_patch(p)
        ax.text(x + w/2, y + h/2, text,
                ha="center", va="center", fontsize=fontsize,
                weight="bold" if bold else "normal")

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#475569",
                                    lw=1.5))

    # 标题
    ax.text(5, 13.5, "中药配伍 AI 预测系统 — 架构",
            ha="center", va="center", fontsize=14, weight="bold")

    # 数据层
    ax.text(0.3, 12.8, "数据层", fontsize=11, weight="bold", color="#1e40af")
    box(0.5, 11.8, 4, 0.8, "HERB 数据库\n(6419 药 / 44595 成分)", c_data)
    box(5.5, 11.8, 4, 0.8, "COCONUT 数据库\n(物种级天然产物)", c_data)
    box(2.5, 10.7, 5, 0.7, "别名映射表\n(31460 条) + 方剂 API", c_data)

    arrow(2.5, 11.8, 5, 11.4)
    arrow(7.5, 11.8, 5, 11.4)
    arrow(5, 11.8, 5, 11.4)

    # 计算层
    ax.text(0.3, 10.1, "计算层", fontsize=11, weight="bold", color="#166534")
    box(0.5, 8.9, 4.2, 1.0, "RDKit 反应引擎\n23 条 SMARTS 规则", c_calc)
    box(5.3, 8.9, 4.2, 1.0, "ADMET 预测\nadmet-ai 2.0.1", c_calc)
    box(2.5, 7.8, 5, 0.7, "产物去重 + 合法性校验", c_calc)

    arrow(5, 10.7, 5, 10.0)
    arrow(2.6, 8.9, 4.5, 8.5)
    arrow(7.4, 8.9, 5.5, 8.5)

    # 输出层
    ax.text(0.3, 7.2, "输出层", fontsize=11, weight="bold", color="#a16207")
    box(0.5, 6.0, 2.6, 1.0, "毒性分子\n(关键词预警)", c_out)
    box(3.5, 6.0, 2.6, 1.0, "ADMET 指标\n(hERG/AMES/ClinTox)", c_out)
    box(6.5, 6.0, 2.6, 1.0, "反应产物\n(SMILES/分子式)", c_out)

    arrow(5, 7.8, 5, 7.1)
    arrow(2.0, 6.0, 3.0, 6.5)
    arrow(5.0, 6.0, 5.0, 6.5)
    arrow(7.8, 6.0, 7.0, 6.5)

    # 应用层
    ax.text(0.3, 5.4, "应用层", fontsize=11, weight="bold", color="#7c3aed")
    box(0.5, 4.2, 2.6, 1.0, "命令行\n(tcm_analyzer.py)", "#e9d5ff")
    box(3.5, 4.2, 2.6, 1.0, "批量分析\n(batch_pairs.py)", "#e9d5ff")
    box(6.5, 4.2, 2.6, 1.0, "LLM 问答\n(llm_agent.py)", "#e9d5ff")

    arrow(2.0, 6.0, 2.0, 5.2)
    arrow(5.0, 6.0, 5.0, 5.2)
    arrow(7.8, 6.0, 7.8, 5.2)

    # 交互层
    ax.text(0.3, 3.6, "交互层", fontsize=11, weight="bold", color="#be123c")
    box(2.5, 2.4, 5, 1.0, "GUI 启动器 (launcher.py)\nLLM 自由问答", "#fecdd3", bold=True)

    arrow(5, 4.2, 5, 3.5)

    # 底部说明
    ax.text(5, 1.6,
            "核心原则：LLM 只做语言组织，不编化学数据\n"
            "所有计算由 RDKit + ADMET 完成，可追溯、可复现",
            ha="center", va="center", fontsize=10,
            style="italic", color="#475569",
            bbox=dict(boxstyle="round,pad=0.5",
                      facecolor="#f1f5f9", edgecolor=c_border))

    plt.tight_layout()
    out = OUT / "FigureS1_architecture.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"[OK] {out.name}")


# ============================================================
# 打包代码
# ============================================================
def build_code_zip():
    """打包核心代码为 zip（不上传 GitHub 的话，用这个交补充材料）"""
    import zipfile
    out = OUT / "Code_snapshot.zip"
    files = [
        "src/db_utils.py",
        "src/tcm_analyzer.py",
        "src/admet_cache.py",
        "src/batch_pairs.py",
        "src/llm_agent.py",
        "src/parse_peifang.py",
        "src/dose_weights.py",
        "src/cascade_reactions.py",
        "scripts/build_alias_map.py",
        "scripts/run_admet_products_all.py",
        "scripts/plot_detox_pathway.py",
        "scripts/plot_groups_herg.py",
        "scripts/plot_compare.py",
        "data/herb_aliases_map.json",
        "logs/batch_groups.csv",
        "docs/reports/admet_products_all_summary.csv",
        "requirements.txt",
    ]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            p = ROOT / rel
            if p.exists():
                z.write(p, rel)
            else:
                print(f"  [warn] {rel} 不存在，跳过")
    print(f"[OK] {out.name}")


def main():
    print(f"输出目录: {OUT}\n")
    build_table_s1()
    build_table_s2()
    build_table_s3()
    build_figure_s1()
    build_code_zip()
    print("\n完成。所有文件在 docs/supplementary/")


if __name__ == "__main__":
    main()