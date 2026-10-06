# -*- coding: utf-8 -*-
r"""
批量跑 10 个配伍的产物 ADMET
- 对每个配伍：跑 tcm_analyzer 拿产物 → 从缓存查 ADMET → 汇总
- 对缓存里没有的产物分子：调用模型预测并写回缓存

输出：
  docs/reports/admet_products_all.csv           # 反应路径级（每行一个产物）
  docs/reports/admet_products_all_summary.csv   # 配伍级汇总（10 行）

用法:
  D:\TCMAI\venv\Scripts\python.exe D:\TCMAI\scripts\run_admet_products_all.py
"""
import sys
import csv
from pathlib import Path
import pandas as pd
from rdkit import RDLogger

RDLogger.DisableLog('rdApp.warning')
RDLogger.DisableLog('rdApp.error')

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from db_utils import find_compounds, find_compounds_coconut
from tcm_analyzer import check_toxicity, predict_reactions, TOXIC_KEYWORDS
from admet_cache import ADMETCache

OUT_ALL = ROOT / "docs" / "reports" / "admet_products_all.csv"
OUT_SUMMARY = ROOT / "docs" / "reports" / "admet_products_all_summary.csv"

# ============================================================
# 10 个配伍（白名单 + COCONUT 物种，与 batch_pairs.py 保持一致）
# (配伍名, [成分源列表])
# 每个源 = (草药名, include, coconut)
# ============================================================
PAIRS = [
    ("附子+甘草", [
        ("附子", ["附子", "制附子", "炮附子", "乌头附子尖"],
         ["aconitum carmichaelii"]),
        ("甘草", ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
         ["glycyrrhiza uralensis", "glycyrrhiza glabra", "glycyrrhiza inflata"]),
    ]),
    ("麻黄+桂枝", [
        ("麻黄", ["麻黄", "炙麻黄"], ["ephedra sinica"]),
        ("桂枝", ["桂枝"], ["cinnamomum cassia"]),
    ]),
    ("知母+石膏", [
        ("知母", ["知母"], ["anemarrhena asphodeloides"]),
    ]),
    ("大黄+芒硝", [
        ("大黄", ["大黄", "酒大黄", "熟大黄", "大黄炭"],
         ["rheum palmatum", "rheum officinale", "rheum tanguticum"]),
    ]),
    ("甘草+海藻", [
        ("甘草", ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
         ["glycyrrhiza uralensis", "glycyrrhiza glabra", "glycyrrhiza inflata"]),
        ("海藻", ["海藻"], ["sargassum pallidum", "sargassum fusiforme"]),
    ]),
    ("人参+藜芦", [
        ("人参", ["人参", "人参花", "人参花蕾", "人参芦",
                  "人参须", "人参叶", "人参子"], ["panax ginseng"]),
        ("藜芦", ["藜芦"], ["veratrum nigrum"]),
    ]),
    ("丁香+郁金", [
        ("丁香", ["丁香"], ["syzygium aromaticum"]),
        ("郁金", ["郁金", "温郁金", "黄丝郁金", "绿丝郁金", "桂郁金"],
         ["curcuma aromatica", "curcuma wenyujin"]),
    ]),
    ("甘草+甘遂", [
        ("甘草", ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
         ["glycyrrhiza uralensis", "glycyrrhiza glabra", "glycyrrhiza inflata"]),
        ("甘遂", ["甘遂"], ["euphorbia kansui"]),
    ]),
    ("半夏+乌头", [
        ("半夏", ["半夏", "法半夏", "制半夏", "半夏曲"], ["pinellia ternata"]),
        ("乌头", ["乌头", "草乌头", "北乌头"],
         ["aconitum carmichaelii", "aconitum kusnezoffii"]),
    ]),
    ("甘草+大戟", [
        ("甘草", ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
         ["glycyrrhiza uralensis", "glycyrrhiza glabra", "glycyrrhiza inflata"]),
        ("大戟", ["京大戟"], ["euphorbia pekinensis"]),
    ]),
]

ADMET_KEYS = ["hERG", "AMES", "ClinTox"]
LIMIT_PER_HERB = 200
LIMIT_COCONUT = 1000


def _avg(lst):
    return round(sum(lst) / len(lst), 3) if lst else None


def _collect_compounds(sources):
    """sources: [(name, include, coconut), ...]"""
    all_c = []
    for name, inc, coco in sources:
        rows = find_compounds(name, include=inc or None, limit=LIMIT_PER_HERB)
        for r in rows:
            r["source"] = name
            all_c.append(r)
        if coco:
            coco_rows = find_compounds_coconut(coco, limit=LIMIT_COCONUT)
            for r in coco_rows:
                r["source"] = f"{name}(COCONUT)"
                all_c.append(r)
    # SMILES 去重
    seen, uniq = set(), []
    for c in all_c:
        smi = c.get("smiles")
        if not smi or smi in seen:
            continue
        seen.add(smi)
        uniq.append(c)
    return uniq


def main():
    cache = ADMETCache()
    print(f"缓存现有: {cache.size()} 条\n")

    # ============================================================
    # 1. 每个配伍：跑反应拿产物
    # ============================================================
    all_products = []   # 全量（反应路径级）
    pair_stats = []     # 配伍级汇总

    for pair_name, sources in PAIRS:
        print(f"=== {pair_name} ===")
        compounds = _collect_compounds(sources)
        print(f"  成分: {len(compounds)}")

        products = predict_reactions(compounds)
        print(f"  产物（反应路径级）: {len(products)}")

        # 成分毒性（从缓存查）
        src_hERGs = []
        for c in compounds:
            rec = cache.get(c["smiles"])
            if rec and rec.get("hERG") is not None:
                src_hERGs.append(float(rec["hERG"]))

        # 产物毒性（先看缓存命中数）
        hit = 0
        for p in products:
            if cache.has(p["smiles"]):
                hit += 1
        print(f"  产物已在缓存: {hit} / {len(products)}")

        # 记录
        for p in products:
            all_products.append({
                "pair": pair_name,
                "from_herb": p.get("from_herb", ""),
                "from_compound": p.get("from_compound", ""),
                "rxn": p.get("rxn", ""),
                "formula": p.get("formula", ""),
                "mw": p.get("mw", None),
                "smiles": p["smiles"],
            })

        pair_stats.append({
            "pair": pair_name,
            "compounds": len(compounds),
            "products": len(products),
            "src_hERG_avg": _avg(src_hERGs),
            "src_hERG_n": len(src_hERGs),
            "_product_smiles": [p["smiles"] for p in products],
        })
        print()

    # ============================================================
    # 2. 收集所有独特产物 SMILES，预测缺失的
    # ============================================================
    uniq_smiles = sorted(set(p["smiles"] for p in all_products))
    print(f"\n=== 产物总去重 SMILES: {len(uniq_smiles)} ===")
    to_predict = [s for s in uniq_smiles if not cache.has(s)]
    print(f"  需预测: {len(to_predict)}")

    if to_predict:
        from admet_ai import ADMETModel
        print("  加载 ADMETModel ...")
        model = ADMETModel()
        # 分批预测，避免一次太大
        BATCH = 500
        total = len(to_predict)
        for i in range(0, total, BATCH):
            chunk = to_predict[i:i + BATCH]
            print(f"  预测 {i + 1}-{i + len(chunk)} / {total} ...")
            preds = model.predict(smiles=chunk)
            df_pred = pd.DataFrame(preds).reset_index()
            df_pred = df_pred.rename(columns={df_pred.columns[0]: "smiles"})
            for _, row in df_pred.iterrows():
                d = row.to_dict()
                smi = d.pop("smiles")
                cache.put(smi, d)
        cache.save()
        print(f"[ok] 缓存更新 → 现有 {cache.size()} 条")

    # ============================================================
    # 3. 组装全量产物表 + 配伍级汇总
    # ============================================================
    rows_all = []
    for p in all_products:
        rec = cache.get(p["smiles"])
        if rec is None:
            continue
        row = dict(p)
        for k in ADMET_KEYS:
            row[k] = rec.get(k)
        row["is_toxic_name"] = bool(
            any(kw in (p["from_compound"] or "").lower() for kw in TOXIC_KEYWORDS)
        )
        rows_all.append(row)

    df_all = pd.DataFrame(rows_all)
    OUT_ALL.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_csv(OUT_ALL, index=False, encoding="utf-8-sig")
    print(f"\n[ok] 全量产物表 → {OUT_ALL}  ({len(df_all)} 行)")

    # 配伍级汇总
    summary_rows = []
    for ps in pair_stats:
        # 找该配伍的所有产物记录
        pair_rows = df_all[df_all["pair"] == ps["pair"]]
        prod_hERGs = [float(v) for v in pair_rows["hERG"].dropna()]
        prod_AMES = [float(v) for v in pair_rows["AMES"].dropna()]
        prod_ClinTox = [float(v) for v in pair_rows["ClinTox"].dropna()]

        # 高毒产物（hERG > 0.5）
        high_herg = sum(1 for v in prod_hERGs if v > 0.5)

        src_herg = ps["src_hERG_avg"]
        prod_herg = _avg(prod_hERGs)
        delta = round(prod_herg - src_herg, 3) if (src_herg and prod_herg) else None

        summary_rows.append({
            "pair": ps["pair"],
            "compounds": ps["compounds"],
            "products": ps["products"],
            "prod_uniq_smiles": len(set(ps["_product_smiles"])),
            "src_hERG_avg": src_herg,
            "prod_hERG_avg": prod_herg,
            "delta_hERG": delta,
            "prod_hERG_high_n": high_herg,
            "prod_AMES_avg": _avg(prod_AMES),
            "prod_ClinTox_avg": _avg(prod_ClinTox),
        })

    df_sum = pd.DataFrame(summary_rows)
    df_sum.to_csv(OUT_SUMMARY, index=False, encoding="utf-8-sig")
    print(f"[ok] 配伍级汇总 → {OUT_SUMMARY}\n")

    # ============================================================
    # 4. 屏幕打印汇总
    # ============================================================
    print("=" * 110)
    print("10 配伍产物 ADMET 汇总")
    print("=" * 110)
    print(f"{'配伍':14s} {'成分':>5s} {'产物':>6s} {'独特':>6s} "
          f"{'成分hERG':>9s} {'产物hERG':>9s} {'Δ':>8s} {'高危产物':>8s}")
    print("-" * 110)
    for r in summary_rows:
        print(f"{r['pair']:14s} {r['compounds']:>5d} {r['products']:>6d} "
              f"{r['prod_uniq_smiles']:>6d} "
              f"{str(r['src_hERG_avg']):>9s} {str(r['prod_hERG_avg']):>9s} "
              f"{str(r['delta_hERG']):>8s} {r['prod_hERG_high_n']:>8d}")

    print("\n[完成] 分析结束")


if __name__ == "__main__":
    main()