# -*- coding: utf-8 -*-
"""
附子 + 甘草 论文配图（修正版：按 name_cn 找药材，英文名过滤成分）
"""
import sys, sqlite3
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT))
from src.visualize import draw_toxic_report

OUT = ROOT / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
DB = str(ROOT / "tcm.db")


def query_compounds(herb_kw, name_kw=None, limit=12):
    """按药材中文名 + 成分英文关键词 查成分"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT herb_id, name_cn FROM herbs WHERE name_cn LIKE ?",
                (f"%{herb_kw}%",))
    herbs = cur.fetchall()
    if not herbs:
        print(f"[warn] herb not found: {herb_kw}")
        conn.close()
        return [], []

    herb_ids = [h[0] for h in herbs]
    herb_names = [h[1] for h in herbs]
    ph = ",".join("?" * len(herb_ids))

    sql = f"""
        SELECT DISTINCT c.name_en, c.smiles, c.mol_weight, c.alias
        FROM herb_compound hc
        JOIN compounds c ON hc.ingredient_id = c.ingredient_id
        WHERE hc.herb_id IN ({ph})
          AND c.smiles IS NOT NULL AND c.smiles != ''
    """
    params = list(herb_ids)

    if name_kw:
        clauses = " OR ".join(["(c.name_en LIKE ? OR c.alias LIKE ?)" for _ in name_kw])
        sql += f" AND ({clauses})"
        for k in name_kw:
            params += [f"%{k}%", f"%{k}%"]

    sql += f" LIMIT {limit}"
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    print(f"[info] {herb_kw}: {len(herb_ids)} herb(s) {herb_names[:3]}, {len(rows)} compound(s)")
    return rows, herb_names


# ============ 附子 ============
FUZI_TOXIC_EN = [
    "aconitine", "hypaconitine", "mesaconitine", "jesaconitine",
    "songorine", "aconine", "benzoylaconine", "napelline",
]
fuzi_rows, _ = query_compounds("附子", FUZI_TOXIC_EN, limit=8)
if not fuzi_rows:
    print("[fallback] 附子：关键词未命中，改取全成分前 8（按分子量排序）")
    fuzi_rows, _ = query_compounds("附子", None, limit=8)

if fuzi_rows:
    draw_toxic_report(
        [(n, s, "Aconitum") for n, s, _, _ in fuzi_rows],
        str(OUT / "fig1_fuzi_toxic.png"),
        title="附子 (Aconitum) 主要毒性生物碱",
        mols_per_row=4,
    )
else:
    print("[ERR] 附子：一个成分都没查到")


# ============ 甘草 ============
GANCAO_MAIN_EN = [
    "glycyrrhizin", "glycyrrhizic", "liquiritin", "isoliquiritin",
    "liquiritigenin", "isoliquiritigenin", "glabridin", "licochalcone",
]
gancao_rows, _ = query_compounds("甘草", GANCAO_MAIN_EN, limit=8)
if not gancao_rows:
    print("[fallback] 甘草：关键词未命中，改取全成分前 8")
    gancao_rows, _ = query_compounds("甘草", None, limit=8)

if gancao_rows:
    draw_toxic_report(
        [(n, s, "Glycyrrhiza") for n, s, _, _ in gancao_rows],
        str(OUT / "fig2_gancao_main.png"),
        title="甘草 (Glycyrrhiza) 主要活性成分",
        mols_per_row=4,
    )
else:
    print("[ERR] 甘草：一个成分都没查到")


print("\n[done] 图保存在:", OUT)