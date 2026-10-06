# -*- coding: utf-8 -*-
r"""批量 ADMET（HERB + COCONUT 双源，COCONUT 每味药 1000）"""
import sys
from pathlib import Path
import pandas as pd
from rdkit import RDLogger

RDLogger.DisableLog('rdApp.warning')
RDLogger.DisableLog('rdApp.error')

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT))
from src.db_utils import find_compounds, find_compounds_coconut
from src.admet_cache import ADMETCache

OUT_CSV = ROOT / "docs" / "reports" / "admet_predictions.csv"

BAD_SMILES = {"not", "none", "n/a", "na", "nan", "null", "unknown",
              "not available", "not found", "-"}


def _is_bad_smiles(smi):
    if not smi or not isinstance(smi, str):
        return True
    s = smi.strip()
    if len(s) < 2:
        return True
    return s.lower() in BAD_SMILES


# ===== 独立 limit =====
LIMIT_PER_HERB = 300      # HERB 每味药（成分数少，300 已足够）
LIMIT_COCONUT = 1000      # COCONUT 每味药（数据量大，放宽到 1000）


# ===== 白名单 + COCONUT 物种 =====
TARGETS = {
    "附子": {
        "include": ["附子", "制附子", "炮附子", "乌头附子尖"],
        "keywords": ["aconitine", "hypaconitine", "mesaconitine",
                     "aconine", "songorine"],
        "priority": ["Aconitine", "Mesaconitine", "Hypaconitine",
                     "Benzoylaconine", "Benzoylmesaconine", "Benzoylhypaconine",
                     "Aconine", "Mesaconine", "Hypaconine"],
        "coconut": ["aconitum carmichaelii"],
    },
    "甘草": {
        "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
        "keywords": ["glycyrrhizin", "liquiritin", "isoliquiritin", "glabridin"],
        "priority": ["Glycyrrhizic acid", "Liquiritin", "Isoliquiritin",
                     "Glabridin", "Liquiritigenin", "Isoliquiritigenin"],
        "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                    "glycyrrhiza inflata"],
    },
    "麻黄": {
        "include": ["麻黄", "炙麻黄"],
        "keywords": ["ephedrine", "pseudoephedrine", "methylephedrine"],
        "priority": [],
        "coconut": ["ephedra sinica"],
    },
    "桂枝": {
        "include": ["桂枝"],
        "keywords": ["cinnamaldehyde", "cinnamic", "coumarin", "cassia"],
        "priority": [],
        "coconut": ["cinnamomum cassia"],
    },
    "知母": {
        "include": ["知母"],
        "keywords": ["sarsasapogenin", "timosaponin", "mangiferin",
                     "neomangiferin"],
        "priority": [],
        "coconut": ["anemarrhena asphodeloides"],
    },
    "石膏": None,
    "大黄": {
        "include": ["大黄", "酒大黄", "熟大黄", "大黄炭"],
        "keywords": ["emodin", "rhein", "chrysophanol", "sennoside",
                     "aloe-emodin", "physcion"],
        "priority": [],
        "coconut": ["rheum palmatum", "rheum officinale", "rheum tanguticum"],
    },
    "芒硝": None,
    "海藻": {
        "include": ["海藻"],
        "keywords": [],
        "priority": [],
        "coconut": ["sargassum pallidum", "sargassum fusiforme"],
    },
    "人参": {
        "include": ["人参", "人参花", "人参花蕾", "人参芦",
                    "人参须", "人参叶", "人参子"],
        "keywords": ["ginsenoside", "panaxadiol", "panaxatriol"],
        "priority": [],
        "coconut": ["panax ginseng"],
    },
    "藜芦": {
        "include": ["藜芦"],
        "keywords": ["veratramine", "veratridine", "jervine",
                     "cevadine", "protoveratrine", "verazine"],
        "priority": [],
        "coconut": ["veratrum nigrum"],
    },
    "丁香": {
        "include": ["丁香"],
        "keywords": ["eugenol", "acetyleugenol", "caryophyllene"],
        "priority": [],
        "coconut": ["syzygium aromaticum"],
    },
    "郁金": {
        "include": ["郁金", "温郁金", "黄丝郁金", "绿丝郁金", "桂郁金"],
        "keywords": ["curcumol", "curdione", "curzerene", "germacrone"],
        "priority": [],
        "coconut": ["curcuma aromatica", "curcuma wenyujin"],
    },
    "甘遂": {
        "include": ["甘遂"],
        "keywords": ["ingenol", "euphol", "tirucallol", "euphadienol"],
        "priority": [],
        "coconut": ["euphorbia kansui"],
    },
    "半夏": {
        "include": ["半夏", "法半夏", "制半夏", "半夏曲"],
        "keywords": ["pinellic", "conicine", "triglochinic"],
        "priority": [],
        "coconut": ["pinellia ternata"],
    },
    "乌头": {
        "include": ["乌头", "草乌头", "北乌头"],
        "keywords": ["aconitine", "mesaconitine", "hypaconitine"],
        "priority": ["Aconitine", "Mesaconitine", "Hypaconitine"],
        "coconut": ["aconitum carmichaelii", "aconitum kusnezoffii"],
    },
    "大戟": {
        "include": ["京大戟"],
        "keywords": ["ingenol", "euphol", "tirucallol"],
        "priority": [],
        "coconut": ["euphorbia pekinensis"],
    },
}


def main():
    all_records = []
    for herb, cfg in TARGETS.items():
        if cfg is None:
            print(f"[skip] {herb}: 矿物药")
            continue

        # HERB
        herb_rows = find_compounds(
            herb,
            name_kws=cfg["keywords"] or None,
            priority_names=cfg["priority"] or None,
            include=cfg.get("include") or None,
            limit=LIMIT_PER_HERB,
        )
        for r in herb_rows:
            r["herb_query"] = herb
        print(f"[info] {herb}: HERB {len(herb_rows)}", end="")

        # COCONUT
        coco_rows = []
        if cfg.get("coconut"):
            coco_rows = find_compounds_coconut(
                cfg["coconut"], limit=LIMIT_COCONUT
            )
            for r in coco_rows:
                r["herb_query"] = herb
            print(f" + COCONUT {len(coco_rows)}")
        else:
            print()

        all_records.extend(herb_rows)
        all_records.extend(coco_rows)

    if not all_records:
        print("[ERR] 没取到任何成分")
        return

    df_all = pd.DataFrame(all_records)
    before = len(df_all)
    df_all = df_all[~df_all["smiles"].apply(_is_bad_smiles)].reset_index(drop=True)
    if before - len(df_all):
        print(f"[filter] 过滤脏 SMILES: {before - len(df_all)} 条")

    unique_smiles = df_all["smiles"].drop_duplicates().tolist()
    print(f"\n[info] 总成分 {len(df_all)}，去重 SMILES {len(unique_smiles)}")

    cache = ADMETCache()
    print(f"[info] 缓存现有 {cache.size()} 条")
    to_predict = [s for s in unique_smiles if not cache.has(s)]
    print(f"[info] 需预测 {len(to_predict)}，命中缓存 {len(unique_smiles) - len(to_predict)}")

    if to_predict:
        from admet_ai import ADMETModel
        print("[info] 加载 ADMETModel ...")
        model = ADMETModel()
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

    records_out = []
    for _, r in df_all.iterrows():
        cached = cache.get(r["smiles"])
        if cached is None:
            continue
        merged = {
            "herb_query": r["herb_query"],
            "herb_name": r.get("herb_name", ""),
            "herb_names": r.get("herb_names", ""),
            "name": r["name"],
            "smiles": r["smiles"],
            "mol_weight": r.get("mol_weight", None),
        }
        merged.update(cached)
        records_out.append(merged)

    df_out = pd.DataFrame(records_out)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[ok] 结果 → {OUT_CSV}  ({len(df_out)} 行 × {len(df_out.columns)} 列)")


if __name__ == "__main__":
    main()