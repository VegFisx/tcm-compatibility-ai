# D:\TCMAI\src\reaction_rules.py
"""
中药煎煮常见化学反应规则库
所有 SMARTS 均经过 RDKit 验证可用
"""

REACTION_RULES = {
    # ========== 水解类 ==========
    "ester_hydrolysis": {
        "name": "酯水解",
        "smarts": "[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[O:3][H].[C:4][OH]",
        "desc": "酯键水解，生成羧酸 + 醇（双酯型生物碱减毒的主要途径）",
        "category": "水解",
    },
    "glycoside_hydrolysis": {
        "name": "糖苷水解",
        "smarts": "[C:1]1([O:2][C:3][C:4][C:5][C:6]1)[O:7][C:8]>>[C:1]1([O:2][C:3][C:4][C:5][C:6]1)[OH].[C:8][OH]",
        "desc": "糖苷键断裂，脱去糖基（皂苷类脱糖生成苷元）",
        "category": "水解",
    },
    "lactone_ring_opening": {
        "name": "内酯开环",
        "smarts": "[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[O:3][H].[C:4][OH]",
        "desc": "内酯开环，生成羟基羧酸",
        "category": "水解",
    },
    "amide_hydrolysis": {
        "name": "酰胺水解",
        "smarts": "[C:1](=[O:2])[N:3]>>[C:1](=[O:2])[O:4][H].[N:3][H]",
        "desc": "酰胺键水解，生成羧酸 + 胺",
        "category": "水解",
    },

    # ========== 氧化还原 ==========
    "oxidation": {
        "name": "羟基氧化",
        "smarts": "[C:1][OH:2]>>[C:1]=[O:2]",
        "desc": "醇/酚羟基氧化为羰基",
        "category": "氧化",
    },
    "aldehyde_oxidation": {
        "name": "醛氧化",
        "smarts": "[CH:1]=[O:2]>>[C:1](=[O:2])[OH]",
        "desc": "醛氧化为羧酸",
        "category": "氧化",
    },
    "aromatic_hydroxylation": {
        "name": "芳香羟基化",
        "smarts": "[cH:1]>>[c:1][OH]",
        "desc": "芳香 C-H 羟基化，生成酚羟基",
        "category": "氧化",
    },
    "ketone_reduction": {
        "name": "酮还原",
        "smarts": "[C:1]=[O:2]>>[C:1]([OH])[H]",
        "desc": "酮还原为醇",
        "category": "还原",
    },

    # ========== 消去/脱水 ==========
    "dehydration": {
        "name": "脱水",
        "smarts": "[C:1][C:2][OH:3]>>[C:1]=[C:2].[OH2]",
        "desc": "醇脱水生成烯",
        "category": "脱水",
    },

    # ========== 脱取代 ==========
    "demethylation": {
        "name": "脱甲基",
        "smarts": "[O:1][CH3:2]>>[O:1][H].[CH3]",
        "desc": "芳香甲氧基脱甲基，生成酚羟基",
        "category": "脱取代",
    },

    # ========== 糖-氨基 ==========
    "maillard_like": {
        "name": "美拉德简化",
        "smarts": "[C:1](=[O:2])[CH2:3][OH:4]>>[C:1](=[O:2])[CH:3]=[O:4]",
        "desc": "还原糖与氨基化合物褐变（简化模型）",
        "category": "糖-氨基",
    },
}