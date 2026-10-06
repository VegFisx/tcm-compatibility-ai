# D:\TCMAI\src\toxic_keywords.py
"""
毒性成分关键词库（含传统有毒中药的特征成分）
用于 RDKit 分析结果的粗筛
"""

TOXIC_KEYWORDS = {
    # ========== 乌头碱类（附子、川乌、草乌） ==========
    "aconitine": "极毒",
    "mesaconitine": "极毒",
    "hypaconitine": "极毒",
    "jiangyouaconitine": "极毒",
    "deoxyaconitine": "极毒",
    "benzoylaconine": "有毒",

    # ========== 士的宁类（马钱子） ==========
    "strychnine": "极毒",
    "brucine": "有毒",
    "vomicine": "有毒",

    # ========== 洋地黄类（洋地黄、夹竹桃） ==========
    "digitoxin": "极毒",
    "digoxin": "极毒",
    "gitoxin": "有毒",
    "digitalis": "极毒",

    # ========== 藜芦类（藜芦） ==========
    "veratramine": "有毒",
    "veratridine": "有毒",
    "jervine": "有毒",
    "cevadine": "有毒",
    "protoveratrine": "极毒",

    # ========== 钩吻类（钩吻/断肠草） ==========
    "gelsemine": "极毒",
    "koumine": "极毒",
    "gelsedine": "有毒",

    # ========== 甘遂/大戟类（大戟科） ==========
    "ingenol": "有毒",         # 巨大戟醇
    "ingenane": "有毒",
    "phorbol": "有毒",         # 巴豆醇
    "euphol": "有毒",          # 大戟醇
    "tirucallol": "有毒",

    # ========== 马兜铃酸类（马兜铃、关木通） ==========
    "aristolochic": "极毒",    # 马兜铃酸
    "aristolactam": "极毒",

    # ========== 吡咯里西啶类（千里光、款冬） ==========
    "senecionine": "有毒",
    "retrorsine": "有毒",
    "monocrotaline": "有毒",

    # ========== 雷公藤类 ==========
    "triptolide": "极毒",
    "wilforlide": "有毒",
    "celastrol": "有毒",

    # ========== 秋水仙（山慈菇） ==========
    "colchicine": "极毒",

    # ========== 其他常见毒物 ==========
    "sanguinarine": "有毒",     # 血根碱
    "chelerythrine": "有毒",
    "berberine": "慎用",        # 黄连素（大剂量慎用）
    "ephedrine": "慎用",        # 麻黄碱（高血压慎用）
    "pseudoephedrine": "慎用",
}


def check_toxicity(compound_name: str):
    """返回命中的关键词及毒性等级"""
    if not compound_name:
        return []
    name = compound_name.lower()
    hits = []
    for kw, level in TOXIC_KEYWORDS.items():
        if kw in name:
            hits.append((kw, level))
    return hits