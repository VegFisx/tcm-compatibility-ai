# -*- coding: utf-8 -*-
r"""
对 tcm_analyzer 预测的产物批量跑 ADMET
- 复用 admet_cache（产物与原成分共用一个缓存池）
- 输出: docs/reports/admet_products.csv（反应路径级）
        docs/reports/admet_products_uniq.csv（独特分子级）

用法:
    D:\TCMAI\venv\Scripts\python.exe D:\TCMAI\scripts\run_admet_products.py
"""
import sys
from pathlib import Path
import pandas as pd
from rdkit import RDLogger

RDLogger.DisableLog('rdApp.warning')
RDLogger.DisableLog('rdApp.error')

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from tcm_analyzer import analyze, check_toxicity, TOXIC_KEYWORDS
from admet_cache import ADMETCache

OUT_ALL = ROOT / "docs" / "reports" / "admet_products.csv"
OUT_UNIQ = ROOT / "docs" / "reports" / "admet_products_uniq.csv"

# 只对这两味药跑产物 ADMET（改这里可换其他配伍）
HERBS = ["附子", "甘草"]
MAX_N = 100
ADMET_KEYS = ["hERG", "AMES", "ClinTox"]


def main():
    print(f"=== 生成 {HERBS} 的产物 ===")
    result = analyze(HERBS, max_n_per_herb=MAX_N)
    products = result["products"]
    print(f"[info] 产物总数（反应路径级）: {len(products)}")

    uniq_smiles = sorted(set(p["smiles"] for p in products))
    print(f"[info] 去重后独特分子数: {len(uniq_smiles)}")

    # ---- 缓存命中检查 ----
    cache = ADMETCache()
    print(f"[info] 缓存现有 {cache.size()} 条")

    to_predict = [s for s in uniq_smiles if not cache.has(s)]
    print(f"[info] 需预测 {len(to_predict)}，命中缓存 {len(uniq_smiles) - len(to_predict)}")

    # ---- 批量预测 ----
    if to_predict:
        from admet_ai import ADMETModel
        print("[info] 加载 ADMETModel ...")
        model = ADMETModel()
        print(f"[info] 预测 {len(to_predict)} 个产物分子 ...")
        preds = model.predict(smiles=to_predict)
        df_pred = pd.DataFrame(preds).reset_index()
        df_pred = df_pred.rename(columns={df_pred.columns[0]: "smiles"})

        for _, row in df_pred.iterrows():
            d = row.to_dict()
            smi = d.pop("smiles")
            cache.put(smi, d)
        cache.save()
        print(f"[ok] 缓存更新 → 现有 {cache.size()} 条")
    else:
        print("[ok] 全部命中缓存")

    # ---- 组装：反应路径级 ----
    rows_all = []
    for p in products:
        rec = cache.get(p["smiles"])
        if rec is None:
            continue
        row = {
            "from_herb": p["from_herb"],
            "from_compound": p["from_compound"],
            "rxn": p["rxn"],
            "formula": p["formula"],
            "mw": p["mw"],
            "smiles": p["smiles"],
        }
        for k in ADMET_KEYS:
            row[k] = rec.get(k)
        # 用产物公式做毒性关键词检查（近似：看 formula 里有没有线索）
        row["is_toxic_name"] = bool(check_toxicity(p["from_compound"]))
        rows_all.append(row)

    df_all = pd.DataFrame(rows_all)
    df_all.to_csv(OUT_ALL, index=False, encoding="utf-8-sig")
    print(f"\n[ok] 反应路径级表 → {OUT_ALL}  ({len(df_all)} 行)")

    # ---- 组装：独特分子级 ----
    df_uniq = df_all.drop_duplicates(subset=["smiles"]).reset_index(drop=True)
    df_uniq.to_csv(OUT_UNIQ, index=False, encoding="utf-8-sig")
    print(f"[ok] 独特分子级表 → {OUT_UNIQ}  ({len(df_uniq)} 行)")

    # ============ 关键分析 ============
    print("\n" + "=" * 70)
    print("关键分析 1: 产物毒性分布")
    print("=" * 70)
    for k in ADMET_KEYS:
        col = df_uniq[k].dropna()
        if len(col) == 0:
            continue
        high = (col > 0.5).sum()
        mid = ((col > 0.3) & (col <= 0.5)).sum()
        low = (col <= 0.3).sum()
        print(f"  {k:8s}: 高(>0.5)={high:3d}  中(0.3-0.5)={mid:3d}  低(<=0.3)={low:3d}  "
              f"均值={col.mean():.3f}")

    # ============ 附子核心减毒链 ============
    print("\n" + "=" * 70)
    print("关键分析 2: 附子核心减毒链（双酯型 → 单酯型 → 醇胺型）")
    print("=" * 70)

    # 从原始成分里找核心的三个分子
    core_names = ["Aconitine", "Benzoylaconine", "Aconine"]
    core_smiles_map = {}
    for c in result["compounds"]:
        if c["name"] in core_names:
            core_smiles_map[c["name"]] = c["smiles"]

    print("\n【原成分】")
    for name in core_names:
        smi = core_smiles_map.get(name)
        if not smi:
            print(f"  {name:20s}  [未找到]")
            continue
        rec = cache.get(smi)
        if rec:
            print(f"  {name:20s}  hERG={rec.get('hERG'):.3f}  "
                  f"AMES={rec.get('AMES'):.3f}  ClinTox={rec.get('ClinTox'):.3f}")
        else:
            print(f"  {name:20s}  [无 ADMET 数据]")

    print("\n【Aconitine 的产物】")
    aco_prods = [p for p in products if p["from_compound"] == "Aconitine"]
    for p in aco_prods:
        rec = cache.get(p["smiles"])
        if not rec:
            continue
        print(f"  --{p['rxn']:8s}-->  MW={p['mw']:7.1f}  "
              f"hERG={rec.get('hERG'):.3f}  "
              f"AMES={rec.get('AMES'):.3f}  "
              f"ClinTox={rec.get('ClinTox'):.3f}  "
              f"{p['formula']}")

    print("\n【Benzoylaconine 的产物】")
    ben_prods = [p for p in products if p["from_compound"] == "Benzoylaconine"]
    for p in ben_prods:
        rec = cache.get(p["smiles"])
        if not rec:
            continue
        print(f"  --{p['rxn']:8s}-->  MW={p['mw']:7.1f}  "
              f"hERG={rec.get('hERG'):.3f}  "
              f"AMES={rec.get('AMES'):.3f}  "
              f"ClinTox={rec.get('ClinTox'):.3f}  "
              f"{p['formula']}")

    # ============ 全局：毒性升高 / 降低统计 ============
    print("\n" + "=" * 70)
    print("关键分析 3: 毒性来源分子 vs 其产物（hERG 均值变化）")
    print("=" * 70)

    # 只统计附子 aconitine 类来源
    acont_sources = [c for c in result["compounds"]
                     if "aconitine" in (c["name"] or "").lower()]
    print(f"\n附子乌头碱类来源分子数: {len(acont_sources)}")

    rows_summary = []
    for c in acont_sources:
        name = c["name"]
        src_rec = cache.get(c["smiles"])
        src_herg = src_rec.get("hERG") if src_rec else None

        prods = [p for p in products if p["from_compound"] == name]
        prod_hergs = []
        for p in prods:
            rec = cache.get(p["smiles"])
            if rec and rec.get("hERG") is not None:
                prod_hergs.append(rec["hERG"])

        if src_herg is None or not prod_hergs:
            continue
        rows_summary.append({
            "compound": name,
            "src_hERG": round(src_herg, 3),
            "prod_hERG_avg": round(sum(prod_hergs) / len(prod_hergs), 3),
            "prod_hERG_min": round(min(prod_hergs), 3),
            "delta": round(sum(prod_hergs) / len(prod_hergs) - src_herg, 3),
        })

    df_sum = pd.DataFrame(rows_summary).sort_values("delta")
    print(f"\n{'来源分子':30s}  {'原hERG':>8s}  {'产物均':>8s}  {'产物最低':>8s}  {'Δ':>8s}")
    print("-" * 70)
    for _, r in df_sum.iterrows():
        print(f"{r['compound'][:30]:30s}  {r['src_hERG']:>8.3f}  "
              f"{r['prod_hERG_avg']:>8.3f}  {r['prod_hERG_min']:>8.3f}  "
              f"{r['delta']:>+8.3f}")

    # 保存 summary
    summary_path = ROOT / "docs" / "reports" / "admet_products_summary.csv"
    df_sum.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"\n[ok] 毒性变化汇总 → {summary_path}")


if __name__ == "__main__":
    main()