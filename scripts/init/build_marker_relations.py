import sqlite3

conn = sqlite3.connect(r"D:\TCMAI\tcm.db")
cur = conn.cursor()

# ---------- 常用中药的标志物清单 ----------
# 格式：药材中文名 → [成分名关键词...]
MARKERS = {
    "人参": ["Ginsenoside", "Notoginsenoside", "Ginseng"],
    "西洋参": ["Ginsenoside", "Quinquenoside"],
    "三七": ["Notoginsenoside", "Ginsenoside", "Panax"],
    "黄连": ["Berberine", "Coptisine", "Palmatine", "Jatrorrhizine", "Epiberberine"],
    "甘草": ["Glycyrrhizin", "Glycyrrhizic", "Liquiritigenin", "Isoliquiritigenin", "Glycyrrhetinic"],
    "附子": ["Aconitine", "Mesaconitine", "Hypaconitine", "Benzoylaconine", "Aconine"],
    "川乌": ["Aconitine", "Mesaconitine", "Hypaconitine"],
    "草乌": ["Aconitine", "Mesaconitine", "Hypaconitine"],
    "大黄": ["Emodin", "Rhein", "Chrysophanol", "Aloeemodin", "Physcion"],
    "麻黄": ["Ephedrine", "Pseudoephedrine", "Norephedrine"],
    "黄芩": ["Baicalin", "Baicalein", "Wogonin", "Oroxylin"],
    "丹参": ["Tanshinone", "Salvianolic", "Danshensu", "Cryptotanshinone"],
    "当归": ["Ferulic", "Z-ligustilide", "Ligustilide", "Angelicide"],
    "川芎": ["Ligustilide", "Ferulic", "Tetramethylpyrazine", "Senkyunolide"],
    "黄芪": ["Astragaloside", "Calycosin", "Formononetin", "Astragalus"],
    "赤芍": ["Paeoniflorin", "Paeonol", "Albiflorin"],
    "白芍": ["Paeoniflorin", "Albiflorin", "Paeonol"],
    "金银花": ["Chlorogenic", "Luteolin", "Lonicerin", "Macranthoidin"],
    "连翘": ["Forsythoside", "Forsythin", "Rengynic", "Arctigenin"],
    "柴胡": ["Saikosaponin", "Bupleurum", "Saikogenin"],
    "半夏": ["Pinellic", "Adenosine", "Ephedrine"],
    "陈皮": ["Hesperidin", "Naringin", "Tangeretin", "Nobiletin"],
    "枳实": ["Hesperidin", "Naringin", "Synephrine"],
    "枳壳": ["Hesperidin", "Naringin", "Synephrine"],
    "五味子": ["Schisandrin", "Gomisin", "Schisantherin"],
    "枸杞": ["Lycium", "Betaine", "Zeaxanthin"],
    "地黄": ["Catalpol", "Rehmannioside", "Aucubin"],
    "山药": ["Dioscin", "Diosgenin", "Allantoin"],
    "茯苓": ["Pachymic", "Poricoic", "Ergosterol"],
    "猪苓": ["Polyporusterone", "Ergosterol"],
    "葛根": ["Puerarin", "Daidzein", "Daidzin", "Genistein"],
    "山楂": ["Vitexin", "Rutin", "Hyperoside", "Chlorogenic"],
    "薄荷": ["Menthol", "Menthone", "Limonene"],
    "菊花": ["Luteolin", "Apigenin", "Chlorogenic"],
    "桑叶": ["Rutin", "Quercetin", "Morin"],
    "牡丹皮": ["Paeonol", "Paeoniflorin"],
    "厚朴": ["Magnolol", "Honokiol", "Magnocurarine"],
    "苍术": ["Atractylenolide", "Atractylodin"],
    "白术": ["Atractylenolide", "Atractylodin"],
    "泽泻": ["Alisol", "Alismol"],
    "石菖蒲": ["Alpha-asarone", "Beta-asarone", "Eugenol"],
    "桃仁": ["Amygdalin", "Prunasin", "Persicoside"],
    "杏仁": ["Amygdalin", "Prunasin"],
    "银杏": ["Ginkgolide", "Bilobalide", "Ginkgetin"],
}

# ---------- 重建 herb_compound ----------
cur.execute("DROP TABLE IF EXISTS herb_compound")
cur.execute("""
CREATE TABLE herb_compound (
    herb_id       TEXT,
    ingredient_id TEXT,
    match_level   TEXT,
    match_source  TEXT,
    UNIQUE(herb_id, ingredient_id)
)
""")

total_relations = 0
herb_hits = 0

for herb_cn, keywords in MARKERS.items():
    # 找药材
    cur.execute("SELECT herb_id FROM herbs WHERE name_cn = ?", (herb_cn,))
    r = cur.fetchone()
    if not r:
        print(f"⚠️ 药材 '{herb_cn}' 不在 herbs 表里")
        continue
    herb_id = r[0]

    matched = set()
    for kw in keywords:
        cur.execute("""
            SELECT ingredient_id
            FROM compounds
            WHERE name_en LIKE ? AND smiles IS NOT NULL
        """, (f"%{kw}%",))
        for (ing_id,) in cur.fetchall():
            matched.add(ing_id)

    for ing_id in matched:
        cur.execute("INSERT OR IGNORE INTO herb_compound VALUES (?,?,?,?)",
                    (herb_id, ing_id, "marker", f"keywords"))
        total_relations += 1

    if matched:
        herb_hits += 1
    print(f"  {herb_cn}: {len(matched)} 个成分")

conn.commit()

print(f"\n===== 汇总 =====")
print(f"匹配成功的药材: {herb_hits}")
print(f"herb_compound 总关系数: {total_relations}")

conn.close()