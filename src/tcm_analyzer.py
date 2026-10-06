# -*- coding: utf-8 -*-
"""
HERB 路线核心引擎
- 从数据库查成分（统一走 db_utils.find_compounds）
- 毒性关键词预警
- RDKit 反应预测（23 条规则，smarts 编译缓存，价态二次校验）
"""
import sys
from pathlib import Path
from typing import List, Dict, Union, Optional

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

RDLogger.DisableLog('rdApp.error')
RDLogger.DisableLog('rdApp.warning')

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))
from db_utils import find_compounds


# ============================================================
# 反应规则库（23 条）
# 分类：水解 7 / 氧化 3 / 还原 2 / 脱除 3 / 加成 3 / 重排 1 / 合成 1 / 其他 3
# ============================================================
REACTIONS = {
    # ============ 水解（7 条）——全部不可逆 ============
    "酯水解": {
        "name": "酯水解",
        "smarts": "[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[O:3][H].[C:4][OH]",
        "desc": "酯键水解为羧酸 + 醇（乌头碱减毒关键）",
        "irreversible": True,
    },
    "糖苷水解": {
        "name": "糖苷水解",
        "smarts": "[C:1]1([O:2][C:3][C:4][C:5][C:6]1)[O:7][C:8]"
                  ">>[C:1]1([O:2][C:3][C:4][C:5][C:6]1)[OH].[OH:7][C:8]",
        "desc": "糖苷键水解（皂苷脱糖）",
        "irreversible": True,
    },
    "酰胺水解": {
        "name": "酰胺水解",
        "smarts": "[C:1](=[O:2])[N:3][C:4]>>[C:1](=[O:2])[O:3][H].[N:3][C:4]",
        "desc": "酰胺水解为羧酸 + 胺",
        "irreversible": True,
    },
    "硫酸酯水解": {
        "name": "硫酸酯水解",
        "smarts": "[S:1](=[O:2])(=[O:3])[O:4][C:5]"
                  ">>[S:1](=[O:2])(=[O:3])[O:4][H].[C:5][OH]",
        "desc": "硫酸酯键水解释放酚/醇（常见于硫酸多糖）",
        "irreversible": True,
    },
    "磷酸酯水解": {
        "name": "磷酸酯水解",
        "smarts": "[P:1](=[O:2])([O:3])[O:4][C:5]"
                  ">>[P:1](=[O:2])([O:3])[O:4][H].[C:5][OH]",
        "desc": "磷酸酯键水解（磷脂、磷酸糖等）",
        "irreversible": True,
    },
    "缩醛水解": {
        "name": "缩醛水解",
        "smarts": "[CX4H1:1]([OX2:2][#6:3])[OX2:4][#6:5]"
                  ">>[CX3H1:1]=[OX1:2].[OH:4][#6:5]",
        "desc": "缩醛水解为醛 + 醇",
        "irreversible": True,
    },
    "半缩醛水解": {
        "name": "半缩醛水解",
        "smarts": "[CX4H1:1]([OH:2])[OX2:3][#6:4]"
                  ">>[CX3H1:1]=[O:2].[OH:3][#6:4]",
        "desc": "半缩醛开环为醛 + 醇（糖类降解起始步）",
        "irreversible": True,
    },

    # ============ 氧化（4 条）——煎煮有氧环境，视为不可逆 ============
    "羟基氧化": {
        "name": "羟基氧化",
        "smarts": "[CH1:1][OH:2]>>[C:1]=[O:2]",
        "desc": "仲醇/酚羟基氧化为羰基",
        "irreversible": True,
    },
    "醛氧化": {
        "name": "醛氧化",
        "smarts": "[CH1:1]=[O:2]>>[C:1](=[O:2])[OH]",
        "desc": "醛氧化为羧酸",
        "irreversible": True,
    },
    "酚氧化成醌": {
        "name": "酚氧化成醌",
        "smarts": "[OH:1][c:2][c:3][OH:4]>>[O:1]=[C:2][C:3]=[O:4]",
        "desc": "邻苯二酚氧化为邻苯醌（多酚聚合起始）",
        "irreversible": True,
    },
    "胺氧化": {
        "name": "胺氧化",
        "smarts": "[CX4H2:1][NX3H2:2]>>[CX3H1:1]=[O:2].[NH3]",
        "desc": "伯胺氧化为醛 + 氨（生物碱降解）",
        "irreversible": True,
    },

    # ============ 还原（2 条）——可逆 ============
    "酮还原": {
        "name": "酮还原",
        "smarts": "[CX3:1](=[OX1:2])[#6:3]>>[CX4:1]([OH])[#6:3]",
        "desc": "酮还原为仲醇",
        "irreversible": False,
    },
    "醌还原": {
        "name": "醌还原",
        "smarts": "[O:1]=[C:2][C:3]=[O:4]>>[OH:1][C:2][C:3][OH:4]",
        "desc": "邻醌还原为邻苯二酚（丹参酮、大黄蒽醌等）",
        "irreversible": False,
    },

    # ============ 脱除（4 条）============
    "脱水": {
        "name": "脱水",
        "smarts": "[CH2:1][CH1:2][OH:3]>>[C:1]=[C:2].[OH2]",
        "desc": "醇脱水生成双键",
        "irreversible": False,
    },
    "脱甲基": {
        "name": "脱甲基",
        "smarts": "[O:1][CH3:2]>>[O:1][H].[CH3][OH]",
        "desc": "芳香甲氧基脱甲基（生成酚 + 甲醇）",
        "irreversible": True,
    },
    "芳香酸脱羧": {
        "name": "芳香酸脱羧",
        "smarts": "[c:1][CX3:2](=[OX1:3])[OX2H:4]>>[c:1][H].[C](=[O])=[O]",
        "desc": "芳香羧酸脱羧，释放 CO₂",
        "irreversible": True,
    },
    "β-酮酸脱羧": {
        "name": "β-酮酸脱羧",
        "smarts": "[CX3:1](=[OX1:2])[CX4:3][CX3:4](=[OX1:5])[OH:6]"
                  ">>[CX3:1](=[OX1:2])[CX4:3]",
        "desc": "β-酮酸脱羧生成酮（有机酸降解）",
        "irreversible": True,
    },

    # ============ 加成 / 水合（3 条）============
    "芳香环羟基化": {
        "name": "芳香环羟基化",
        "smarts": "[cH:1]:[c:2]>>[c:1]([OH]):[c:2]",
        "desc": "芳环 C-H 羟基化为酚",
        "irreversible": True,
    },
    "烯烃水合": {
        "name": "烯烃水合",
        "smarts": "[C:1]=[C:2]>>[C:1][C:2][OH]",
        "desc": "双键隐含加水生成醇",
        "irreversible": False,
    },
    "α,β-不饱和羰基水合": {
        "name": "α,β-不饱和羰基水合",
        "smarts": "[C:1]=[C:2][C:3]=[O:4]>>[C:1][C:2]([OH])[C:3]=[O:4]",
        "desc": "α,β-不饱和羰基隐含水合",
        "irreversible": False,
    },

    # ============ 重排（1 条）============
    "酮-烯醇化": {
        "name": "酮-烯醇化",
        "smarts": "[CX3:1](=[OX1:2])[CX4H2:3]>>[C:1]([OH:2])=[C:3]",
        "desc": "酮/醛的 α-H 烯醇化（影响后续反应）",
        "irreversible": False,
    },

    # ============ 合成 / 反向（1 条）============
    "酯化": {
        "name": "酯化",
        "smarts": "[OX2H:1][CX4:2][CX3:3](=[OX1:4])[OX2H:5]"
                  ">>[O:1]1[CX4:2][CX3:3](=[OX1:4])[OH:5]1",
        "desc": "分子内酯化（γ/δ-羟基酸 → 内酯）",
        "irreversible": False,
    },

    # ============ 其他（1 条）============
    "美拉德简化": {
        "name": "美拉德简化",
        "smarts": "[C:1](=[O:2])[CH2:3][OH:4]>>[C:1](=[O:2])[CH:3]=[O:4]",
        "desc": "还原糖与氨基化合物褐变（简化模型）",
        "irreversible": True,
    },
}

# 按规则限流（每分子每规则最多保留几个产物）
RULE_LIMITS = {
    # 宽泛规则收紧
    "羟基氧化": 2,
    "脱甲基": 2,
    "芳香环羟基化": 1,
    "芳香酸脱羧": 1,
    "酮还原": 1,
    "醌还原": 2,
    "缩醛水解": 1,
    "半缩醛水解": 2,
    "酚氧化成醌": 1,         # 多酚位点太多
    "胺氧化": 2,
    "酮-烯醇化": 1,
    "β-酮酸脱羧": 2,
    # 中等
    "糖苷水解": 3,
    "酯水解": 3,
    "酰胺水解": 3,
    "硫酸酯水解": 3,
    "磷酸酯水解": 3,
    "脱水": 3,
    "醛氧化": 3,
    "烯烃水合": 1,
    "α,β-不饱和羰基水合": 1,
    "酯化": 2,
    "美拉德简化": 3,
}

_RXN_CACHE = None
_LAST_RXN_STATS: Dict[str, int] = {}


def get_reactions():
    global _RXN_CACHE
    if _RXN_CACHE is None:
        compiled = {}
        for key, rule in REACTIONS.items():
            try:
                compiled[key] = {
                    "name": rule["name"],
                    "rxn": AllChem.ReactionFromSmarts(rule["smarts"]),
                    "desc": rule.get("desc", ""),
                    "irreversible": rule.get("irreversible", False),
                }
            except Exception as e:
                print(f"[warn] 规则 {key} 编译失败: {e}")
        _RXN_CACHE = compiled
    return _RXN_CACHE

# ============================================================
# 毒性关键词（约 40 个）
# ============================================================
TOXIC_KEYWORDS = [
    "aconitine", "mesaconitine", "hypaconitine", "jiangyouaconitine",
    "deoxyaconitine", "benzoylaconine",
    "strychnine", "brucine", "vomicine",
    "digitoxin", "digoxin", "gitoxin", "digitalis",
    "veratramine", "veratridine", "jervine", "cevadine", "protoveratrine",
    "gelsemine", "koumine", "gelsedine",
    "ingenol", "ingenane", "phorbol", "euphol", "tirucallol",
    "aristolochic", "aristolactam",
    "senecionine", "retrorsine", "monocrotaline",
    "triptolide", "wilforlide", "celastrol",
    "colchicine",
    "sanguinarine", "chelerythrine",
]


def check_toxicity(compound: Union[dict, str, tuple]) -> List[str]:
    if isinstance(compound, dict):
        name = (compound.get("name") or "").lower()
    elif isinstance(compound, str):
        name = compound.lower()
    elif isinstance(compound, (list, tuple)):
        name = (compound[1] if len(compound) > 1 else "").lower()
    else:
        name = ""
    return [kw for kw in TOXIC_KEYWORDS if kw in name]


# ============================================================
# 反应预测
# ============================================================
def _valid_product(mol, min_mw=100, min_heavy=10) -> bool:
    try:
        flag = Chem.SanitizeMol(mol, catchErrors=True)
        if flag != Chem.SanitizeFlags.SANITIZE_NONE:
            return False
    except Exception:
        return False
    if Descriptors.MolWt(mol) < min_mw:
        return False
    if mol.GetNumHeavyAtoms() < min_heavy:
        return False
    return True


def predict_reactions(compounds, min_mw=100, min_heavy=10,
                      rule_limits: Optional[Dict[str, int]] = None) -> List[Dict]:
    global _LAST_RXN_STATS
    reactions = get_reactions()
    if rule_limits is None:
        rule_limits = RULE_LIMITS

    rxn_stats = {rinfo["name"]: 0 for rinfo in reactions.values()}
    seen = set()
    products = []

    for comp in compounds:
        if isinstance(comp, dict):
            smi = comp.get("smiles")
            name = comp.get("name", "(无名)")
            herb = comp.get("herb_name") or comp.get("source", "")
        elif isinstance(comp, (list, tuple)) and len(comp) >= 3:
            herb, name, smi = comp[0], comp[1], comp[2]
        else:
            continue

        if not smi:
            continue
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue

        for rkey, rinfo in reactions.items():
            rule_name = rinfo["name"]
            limit = rule_limits.get(rule_name, None)
            try:
                res = rinfo["rxn"].RunReactants((mol,))
            except Exception:
                continue

            rule_count = 0
            for prod_set in res:
                if limit is not None and rule_count >= limit:
                    break
                for p in prod_set:
                    if not _valid_product(p, min_mw, min_heavy):
                        continue
                    try:
                        new_smi = Chem.MolToSmiles(p)
                    except Exception:
                        continue
                    dedup_key = (new_smi, name)
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)
                    rule_count += 1
                    rxn_stats[rule_name] += 1
                    products.append({
                        "from_herb": herb,
                        "from_compound": name,
                        "rxn": rule_name,
                        "formula": rdMolDescriptors.CalcMolFormula(p),
                        "smiles": new_smi,
                        "mw": round(Descriptors.MolWt(p), 1),
                    })

    # 原地更新，保证外部 import 的引用能读到
    _LAST_RXN_STATS.clear()
    _LAST_RXN_STATS.update(rxn_stats)
    return products


# ============================================================
# 主分析接口
# ============================================================
def analyze(herb_names: List[str], max_n_per_herb: int = 100,
            rule_limits: Optional[Dict[str, int]] = None) -> Dict:
    all_compounds = []
    for h in herb_names:
        rows = find_compounds(h, limit=max_n_per_herb)
        for r in rows:
            r["source"] = h
            all_compounds.append(r)

    seen, uniq = set(), []
    for c in all_compounds:
        key = c.get("smiles")
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(c)

    warnings = []
    for c in uniq:
        tox = check_toxicity(c)
        if tox:
            src = c.get("herb_name") or c.get("source", "?")
            warnings.append(f"  [!] [{src}] {c['name']} — {tox}")

    products = predict_reactions(uniq, rule_limits=rule_limits)

    return {
        "herbs": herb_names,
        "total_compounds": len(uniq),
        "compounds": uniq,
        "toxicity_warnings": warnings,
        "total_products": len(products),
        "products": products,
        "rxn_stats": _LAST_RXN_STATS,
    }


if __name__ == "__main__":
    import sys
    import re

    # 只按 逗号/加号/顿号/分号 切分。空格不算分隔符。
    SEPARATOR = r"[,，+、;；]+"

    def parse_herbs(raw):
        # 切分后去掉首尾空格，但保留药名内部空格（拉丁学名等）
        return [h.strip() for h in re.split(SEPARATOR, raw) if h.strip()]

    def get_raw_from_input():
        print("=== 中药配伍分析 ===")
        print("输入药材名，用 逗号/加号/顿号 分隔")
        print("例如：附子,甘草   或   附子+甘草   或   附子、甘草")
        print("输入 q 退出\n")
        raw = input("药材 > ").strip()

        if raw.lower() in ("q", "quit", "exit", "退出"):
            print("已退出。")
            sys.exit(0)
        if not raw:
            print("\n[提示] 没有输入药材名，已退出。")
            sys.exit(0)
        return raw

    # ---- 解析输入 ----
    if len(sys.argv) > 1:
        # 命令行：把所有参数用空格拼回来，再按分隔符切
        raw = " ".join(sys.argv[1:])
    else:
        raw = get_raw_from_input()

    herbs = parse_herbs(raw)

    # ---- 提示：如果只切出一段，且里面有空格，可能用户想用空格分隔 ----
    if len(herbs) == 1 and " " in herbs[0]:
        print(f"\n[提示] 检测到输入里的空格：")
        print(f"       当前当成一个药名处理 → 「{herbs[0]}」")
        print(f"       如果你想分析多味药，请用 逗号/加号/顿号 分隔：")
        print(f"       例如：附子,甘草   或   附子+甘草")
        print(f"       如果这是单个带空格的药名（如拉丁学名），忽略本提示。\n")

    if not herbs:
        print("[提示] 药材列表为空，已退出。")
        sys.exit(0)

    # ---- 跑分析 ----
    print(f"\n分析药材: {herbs}\n")
    result = analyze(herbs, max_n_per_herb=100)

    print(f"成分总数: {result['total_compounds']}  (HERB 单源；如需 COCONUT 补充，请跑 batch_pairs.py)")
    print(f"\n毒性预警 ({len(result['toxicity_warnings'])} 条):")
    for w in result["toxicity_warnings"][:10]:
        print(w)
    if len(result["toxicity_warnings"]) > 10:
        print(f"  ... (还有 {len(result['toxicity_warnings']) - 10} 条)")

    print(f"\n预测产物数: {result['total_products']}")
    print("\n=== 每条规则贡献 ===")
    for name, count in sorted(result["rxn_stats"].items(),
                              key=lambda x: -x[1]):
        if count > 0:
            print(f"  {name:16s} : {count}")