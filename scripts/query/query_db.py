import sqlite3

conn = sqlite3.connect("tcm.db")
cur = conn.cursor()

cur.execute("""
    SELECT h.herb_name, c.compound_name
    FROM herbs h
    JOIN herb_compound hc ON h.herb_id = hc.herb_id
    JOIN compounds c ON hc.compound_id = c.compound_id
    WHERE h.herb_name = '附子'
""")

for row in cur.fetchall():
    print(row)

conn.close()
