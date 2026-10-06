# -*- coding: utf-8 -*-
"""
批量跑经典配伍 / 复方（HERB + COCONUT 双源，支持 N 味药）
- 2 味：对药（十八反、相畏...）
- 3-8 味：经典复方（四逆汤、麻黄汤...）
"""
import sys
import csv
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

from db_utils import find_compounds, find_compounds_coconut, collect_compounds
from tcm_analyzer import check_toxicity, predict_reactions
from admet_cache import ADMETCache

LIMIT_PER_HERB = 200
LIMIT_COCONUT = 1000

# ============================================================
# 复方定义：每个 group 一个 dict，herbs 是 list（N 味）
# 每味药 = {"cn": "...", "include": [...], "coconut": [...]}
# ============================================================
GROUPS = [
    # ============ 对药（原有 10 个）============
    {
        "name": "附子+甘草", "relation": "相畏/减毒",
        "herbs": [
            {"cn": "附子", "include": ["附子", "制附子", "炮附子", "乌头附子尖"],
             "coconut": ["aconitum carmichaelii"]},
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
        ],
    },
    {
        "name": "麻黄+桂枝", "relation": "相须",
        "herbs": [
            {"cn": "麻黄", "include": ["麻黄", "炙麻黄"], "coconut": ["ephedra sinica"]},
            {"cn": "桂枝", "include": ["桂枝"], "coconut": ["cinnamomum cassia"]},
        ],
    },
    {
        "name": "知母+石膏", "relation": "相须",
        "herbs": [
            {"cn": "知母", "include": ["知母"], "coconut": ["anemarrhena asphodeloides"]},
        ],
    },
    {
        "name": "大黄+芒硝", "relation": "相使",
        "herbs": [
            {"cn": "大黄", "include": ["大黄", "酒大黄", "熟大黄", "大黄炭"],
             "coconut": ["rheum palmatum", "rheum officinale", "rheum tanguticum"]},
        ],
    },
    {
        "name": "甘草+海藻", "relation": "十八反",
        "herbs": [
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
            {"cn": "海藻", "include": ["海藻"],
             "coconut": ["sargassum pallidum", "sargassum fusiforme"]},
        ],
    },
    {
        "name": "人参+藜芦", "relation": "十八反",
        "herbs": [
            {"cn": "人参", "include": ["人参", "人参花", "人参花蕾", "人参芦",
                                       "人参须", "人参叶", "人参子"],
             "coconut": ["panax ginseng"]},
            {"cn": "藜芦", "include": ["藜芦"], "coconut": ["veratrum nigrum"]},
        ],
    },
    {
        "name": "丁香+郁金", "relation": "十九畏",
        "herbs": [
            {"cn": "丁香", "include": ["丁香"], "coconut": ["syzygium aromaticum"]},
            {"cn": "郁金", "include": ["郁金", "温郁金", "黄丝郁金", "绿丝郁金", "桂郁金"],
             "coconut": ["curcuma aromatica", "curcuma wenyujin"]},
        ],
    },
    {
        "name": "甘草+甘遂", "relation": "十八反",
        "herbs": [
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
            {"cn": "甘遂", "include": ["甘遂"], "coconut": ["euphorbia kansui"]},
        ],
    },
    {
        "name": "半夏+乌头", "relation": "十八反",
        "herbs": [
            {"cn": "半夏", "include": ["半夏", "法半夏", "制半夏", "半夏曲"],
             "coconut": ["pinellia ternata"]},
            {"cn": "乌头", "include": ["乌头", "草乌头", "北乌头"],
             "coconut": ["aconitum carmichaelii", "aconitum kusnezoffii"]},
        ],
    },
    {
        "name": "甘草+大戟", "relation": "十八反",
        "herbs": [
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
            {"cn": "大戟", "include": ["京大戟"], "coconut": ["euphorbia pekinensis"]},
        ],
    },

    # ============ 经典复方（3-5 味）============
    {
        "name": "四逆汤", "relation": "温里剂（3 味）",
        "herbs": [
            {"cn": "附子", "include": ["附子", "制附子", "炮附子", "乌头附子尖"],
             "coconut": ["aconitum carmichaelii"]},
            {"cn": "干姜", "include": ["干姜"], "coconut": ["zingiber officinale"]},
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
        ],
    },
    {
        "name": "四君子汤", "relation": "补益剂（4 味）",
        "herbs": [
            {"cn": "人参", "include": ["人参", "人参须"], "coconut": ["panax ginseng"]},
            {"cn": "白术", "include": ["白术"], "coconut": ["atractylodes macrocephala"]},
            {"cn": "茯苓", "include": ["茯苓"], "coconut": ["poria cocos"]},
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
        ],
    },
    {
        "name": "理中丸", "relation": "温中剂（4 味）",
        "herbs": [
            {"cn": "人参", "include": ["人参", "人参须"], "coconut": ["panax ginseng"]},
            {"cn": "干姜", "include": ["干姜"], "coconut": ["zingiber officinale"]},
            {"cn": "白术", "include": ["白术"], "coconut": ["atractylodes macrocephala"]},
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
        ],
    },
    {
        "name": "麻黄汤", "relation": "解表剂（4 味）",
        "herbs": [
            {"cn": "麻黄", "include": ["麻黄", "炙麻黄"], "coconut": ["ephedra sinica"]},
            {"cn": "桂枝", "include": ["桂枝"], "coconut": ["cinnamomum cassia"]},
            {"cn": "杏仁", "include": ["杏仁", "苦杏仁", "甜杏仁"],
             "coconut": ["prunus armeniaca"]},
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
        ],
    },
    {
        "name": "桂枝汤", "relation": "解表剂（5 味）",
        "herbs": [
            {"cn": "桂枝", "include": ["桂枝"], "coconut": ["cinnamomum cassia"]},
            {"cn": "白芍", "include": ["白芍", "芍药"], "coconut": ["paeonia lactiflora"]},
            {"cn": "生姜", "include": ["生姜", "姜"], "coconut": ["zingiber officinale"]},
            {"cn": "大枣", "include": ["大枣", "红枣", "枣"], "coconut": ["ziziphus jujuba"]},
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
        ],
    },
    {
        "name": "大承气汤", "relation": "泻下剂（4 味）",
        "herbs": [
            {"cn": "大黄", "include": ["大黄"], "coconut": ["rheum palmatum"]},
            {"cn": "厚朴", "include": ["厚朴"], "coconut": ["magnolia officinalis"]},
            {"cn": "枳实", "include": ["枳实"], "coconut": ["citrus aurantium"]},
        ],
    },
    {
        "name": "六味地黄丸", "relation": "补益剂（6 味）",
        "herbs": [
            {"cn": "熟地黄", "include": ["熟地黄", "熟地", "地黄"],
             "coconut": ["rehmannia glutinosa"]},
            {"cn": "山药", "include": ["山药"], "coconut": ["dioscorea opposita"]},
            {"cn": "山茱萸", "include": ["山茱萸"], "coconut": ["cornus officinalis"]},
            {"cn": "泽泻", "include": ["泽泻"], "coconut": ["alisma plantago-aquatica"]},
            {"cn": "牡丹皮", "include": ["牡丹皮", "丹皮"], "coconut": ["paeonia suffruticosa"]},
            {"cn": "茯苓", "include": ["茯苓"], "coconut": ["poria cocos"]},
        ],
    },
    {
        "name": "小柴胡汤", "relation": "和解剂（7 味）",
        "herbs": [
            {"cn": "柴胡", "include": ["柴胡"], "coconut": ["bupleurum chinense"]},
            {"cn": "黄芩", "include": ["黄芩"], "coconut": ["scutellaria baicalensis"]},
            {"cn": "半夏", "include": ["半夏", "法半夏", "制半夏"],
             "coconut": ["pinellia ternata"]},
            {"cn": "生姜", "include": ["生姜", "姜"], "coconut": ["zingiber officinale"]},
            {"cn": "人参", "include": ["人参", "人参须"], "coconut": ["panax ginseng"]},
            {"cn": "大枣", "include": ["大枣", "红枣", "枣"], "coconut": ["ziziphus jujuba"]},
            {"cn": "甘草", "include": ["甘草", "炙甘草", "光果甘草", "胀果甘草"],
             "coconut": ["glycyrrhiza uralensis", "glycyrrhiza glabra",
                         "glycyrrhiza inflata"]},
        ],
    },
]

ADMET_KEYS = ["hERG", "AMES", "ClinTox"]


# ============================================================
# 工具函数
# ============================================================
def _avg(lst):
    return round(sum(lst) / len(lst), 3) if lst else None


def _collect_compounds(herbs):
    """调用 db_utils 统一入口（与 llm_agent 口径一致）"""
    return collect_compounds(herbs, herb_limit=LIMIT_PER_HERB,
                             coconut_limit=LIMIT_COCONUT)


def _admet_summary(compounds, cache):
    buckets = {k: [] for k in ADMET_KEYS}
    hits = 0
    for c in compounds:
        rec = cache.get(c["smiles"])
        if not rec:
            continue
        hits += 1
        for k in ADMET_KEYS:
            v = rec.get(k)
            if v is not None:
                buckets[k].append(float(v))
    return {
        "admet_hit": hits,
        "hERG_avg": _avg(buckets["hERG"]),
        "AMES_avg": _avg(buckets["AMES"]),
        "ClinTox_avg": _avg(buckets["ClinTox"]),
    }


def run_group(group, cache=None):
    """跑一个复方（N 味）"""
    compounds = _collect_compounds(group["herbs"])
    toxic = [c for c in compounds if check_toxicity(c)]
    row = {
        "compounds": len(compounds),
        "toxic": len(toxic),
        "products": len(predict_reactions(compounds)),
    }
    if cache is not None:
        row.update(_admet_summary(compounds, cache))
    return row


# ============================================================
# 主流程
# ============================================================
def main():
    cache = ADMETCache()
    print(f"ADMET 缓存: {cache.size()} 条")
    print(f"共 {len(GROUPS)} 组（对药 + 复方）\n")

    rows = []
    for group in GROUPS:
        name = group["name"]
        relation = group["relation"]
        n_herbs = len(group["herbs"])
        print(f"处理: {name} ({relation}, {n_herbs} 味) ...")

        g = run_group(group, cache=cache)

        row = {
            "复方": name,
            "传统关系": relation,
            "药味数": n_herbs,
            "成分数": g["compounds"],
            "毒性分子": g["toxic"],
            "产物数": g["products"],
            "hERG": g.get("hERG_avg"),
            "AMES": g.get("AMES_avg"),
            "ClinTox": g.get("ClinTox_avg"),
        }
        rows.append(row)

        print(f"  成分 {g['compounds']} / 毒性 {g['toxic']} / "
              f"产物 {g['products']}")
        if cache.size():
            print(f"  ADMET: hERG={g.get('hERG_avg')} "
                  f"AMES={g.get('AMES_avg')} "
                  f"ClinTox={g.get('ClinTox_avg')} "
                  f"(命中 {g.get('admet_hit', 0)})")
        print()

    headers = ["复方", "传统关系", "药味数", "成分数", "毒性分子", "产物数",
               "hERG", "AMES", "ClinTox"]

    print("\n" + "=" * 110)
    print("Markdown 汇总表")
    print("=" * 110 + "\n")
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for r in rows:
        print("| " + " | ".join(str(r[h]) for h in headers) + " |")

    csv_path = ROOT / "logs" / "batch_groups.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV 已保存: {csv_path}")


if __name__ == "__main__":
    main()