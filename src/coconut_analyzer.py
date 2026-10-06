# D:\TCMAI\src\coconut_analyzer.py
"""
COCONUT 物种级成分分析引擎
输入：物种拉丁名（可多个）
输出：成分列表 + RDKit 反应预测 + 毒性关键词预警
"""
import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path

# --- 关闭 RDKit 警告刷屏 ---
from rdkit import RDLogger
RDLogger.DisableLog("rdApp.*")

from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit.Chem import rdMolDescriptors

# 引入独立规则库
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reaction_rules import REACTION_RULES

# ==================== 配置 ====================
COCONUT_DB = r"D:\TCMAI\coconut.db"

from toxic_keywords import check_toxicity as _check_tox

def check_toxicity(compound):
    name = (compound.get("name") or "")
    hits = _check_tox(name)
    return [kw for kw, _ in hits]

# ==================== 查询 ====================
def query_species_compounds(species_list, max_per_species=200):
    conn = sqlite3.connect(COCONUT_DB)
    cur = conn.cursor()
    result = {}
    for sp in species_list:
        cur.execute("""
        SELECT c.cnp_id, c.name, c.formula, c.np_likeness, c.smiles
        FROM species_compound sc
        JOIN compounds c ON c.cnp_id = sc.cnp_id
        WHERE sc.species = ?
          AND c.smiles IS NOT NULL AND c.smiles != ''
        LIMIT ?
        """, (sp.lower().strip(), max_per_species))
        rows = cur.fetchall()
        result[sp] = [
            {"cnp_id": r[0], "name": r[1] or "(无名称)",
             "formula": r[2], "np_likeness": r[3], "smiles": r[4],
             "source_species": sp}
            for r in rows
        ]
    conn.close()
    return result


def query_genus_compounds(genus, max_n=300):
    conn = sqlite3.connect(COCONUT_DB)
    cur = conn.cursor()
    cur.execute("""
    SELECT c.cnp_id, c.name, c.formula, c.np_likeness, c.smiles
    FROM genus_compound gc
    JOIN compounds c ON c.cnp_id = gc.cnp_id
    WHERE gc.genus = ?
      AND c.smiles IS NOT NULL AND c.smiles != ''
    LIMIT ?
    """, (genus.lower().strip(), max_n))
    rows = cur.fetchall()
    conn.close()
    return [
        {"cnp_id": r[0], "name": r[1] or "(无名称)",
         "formula": r[2], "np_likeness": r[3], "smiles": r[4]}
        for r in rows
    ]


# ==================== RDKit 反应预测 ====================
MIN_HEAVY_ATOMS = 10
MIN_MW = 100.0


def apply_reactions(smiles, max_products=20):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    seen_products = set()
    products = []
    for rule_id, rule in REACTION_RULES.items():
        try:
            rxn = AllChem.ReactionFromSmarts(rule["smarts"])
            outs = rxn.RunReactants((mol,))
            for out_tuple in outs[:max_products]:
                for product in out_tuple:
                    try:
                        Chem.SanitizeMol(product)
                        if product.GetNumHeavyAtoms() < MIN_HEAVY_ATOMS:
                            continue
                        mw = rdMolDescriptors.CalcExactMolWt(product)
                        if mw < MIN_MW:
                            continue
                        p_smi = Chem.MolToSmiles(product)
                        if p_smi in seen_products:
                            continue
                        seen_products.add(p_smi)
                        products.append({
                            "rule": rule_id,
                            "rule_name": rule["name"],
                            "product_smiles": p_smi,
                            "product_formula": rdMolDescriptors.CalcMolFormula(product),
                            "product_mw": round(mw, 2),
                        })
                    except Exception:
                        continue
        except Exception:
            continue
    return products


# ==================== 毒性预警 ====================
TOXIC_KEYWORDS = [
    # 乌头碱类（附子、川乌、草乌）
    "aconitine", "mesaconitine", "hypaconitine", "jiangyouaconitine",
    "deoxyaconitine", "benzoylaconine",
    # 士的宁（马钱子）
    "strychnine", "brucine", "vomicine",
    # 洋地黄类
    "digitoxin", "digoxin", "gitoxin", "digitalis",
    # 藜芦类
    "veratramine", "veratridine", "jervine", "cevadine", "protoveratrine",
    # 钩吻类
    "gelsemine", "koumine", "gelsedine",
    # 大戟科毒性二萜
    "ingenol", "ingenane", "phorbol", "euphol", "tirucallol",
    # 马兜铃酸
    "aristolochic", "aristolactam",
    # 吡咯里西啶
    "senecionine", "retrorsine", "monocrotaline",
    # 雷公藤
    "triptolide", "wilforlide", "celastrol",
    # 秋水仙
    "colchicine",
    # 其他
    "sanguinarine", "chelerythrine",
]


def check_toxicity(compound):
    name = (compound.get("name") or "").lower()
    return [kw for kw in TOXIC_KEYWORDS if kw in name]


# ==================== 主分析 ====================
def analyze(species_list, max_per_species=100, do_reaction=True, max_react=50):
    result = {
        "input_species": species_list,
        "compounds_by_species": {},
        "all_compounds": [],
        "toxic_hits": [],
        "reactions": {},
        "summary": {},
    }

    compounds_by_species = query_species_compounds(species_list, max_per_species)
    all_compounds = []
    for sp, items in compounds_by_species.items():
        # 按 canonical SMILES 去重
        seen = set()
        deduped = []
        for c in items:
            smi = c.get("smiles")
            if not smi:
                continue
            try:
                key = Chem.MolToSmiles(Chem.MolFromSmiles(smi))
            except Exception:
                continue
            if key not in seen:
                seen.add(key)
                deduped.append(c)
        result["compounds_by_species"][sp] = deduped
        all_compounds.extend(deduped)
    result["all_compounds"] = all_compounds

    for c in all_compounds:
        hits = check_toxicity(c)
        if hits:
            result["toxic_hits"].append({
                "name": c["name"], "species": c["source_species"],
                "hits": hits, "smiles": c["smiles"],
            })

    if do_reaction:
        for c in all_compounds[:max_react]:
            prods = apply_reactions(c["smiles"])
            if prods:
                result["reactions"][c["cnp_id"]] = {
                    "name": c["name"],
                    "species": c["source_species"],
                    "parent_smiles": c["smiles"],
                    "products": prods,
                }

    total_products = sum(len(v["products"]) for v in result["reactions"].values())
    result["summary"] = {
        "species_count": len(species_list),
        "compound_count": len(all_compounds),
        "toxic_count": len(result["toxic_hits"]),
        "reaction_rules": list(REACTION_RULES.keys()),
        "molecules_reacted": len(result["reactions"]),
        "total_products": total_products,
    }
    return result


# ==================== 输出 ====================
def print_report(r):
    print("=" * 60)
    print("COCONUT 物种级成分分析")
    print("=" * 60)
    s = r["summary"]
    print(f"输入物种: {r['input_species']}")
    print(f"成分总数: {s['compound_count']}")
    print()
    print("[毒性关键词初筛]")
    if not r["toxic_hits"]:
        print("  无命中")
    else:
        seen = set()
        for t in r["toxic_hits"]:
            key = (t["name"], t["species"])
            if key in seen:
                continue
            seen.add(key)
            print(f"  ⚠ {t['name']} ({t['species']}) → {t['hits']}")
    print()
    print("[RDKit 反应预测]")
    for cnp, info in list(r["reactions"].items())[:20]:
        print(f"  {info['name'][:60]} ({info['species']}) → {len(info['products'])} 个产物")
        for p in info["products"][:3]:
            print(f"      [{p['rule_name']}] {p['product_formula']}")
    print()
    print("=" * 60)
    print("汇总")
    print("=" * 60)
    print(f"物种数: {s['species_count']}")
    print(f"成分总数: {s['compound_count']}")
    print(f"毒性预警: {s['toxic_count']}")
    print(f"反应规则数: {len(s['reaction_rules'])}")
    print(f"参与反应分子数: {s['molecules_reacted']}")
    print(f"预测产物总数: {s['total_products']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("species", nargs="+")
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--no-reaction", action="store_true")
    parser.add_argument("--json", help="输出 JSON 到指定文件")
    args = parser.parse_args()

    r = analyze(args.species, args.max, not args.no_reaction)
    print_report(r)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        print(f"\nJSON 已保存: {args.json}")


if __name__ == "__main__":
    main()