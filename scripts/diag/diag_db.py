import sqlite3

c = sqlite3.connect(r'D:\TCMAI\tcm.db')
cur = c.cursor()

print('=== TABLES ===')
for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    print(' ', t[0])
print()

for tbl in ['compounds', 'herb_compound', 'herbs']:
    print('=== ' + tbl + ' COLUMNS ===')
    try:
        cols = [r[1] for r in cur.execute('PRAGMA table_info(' + tbl + ')').fetchall()]
        print(' ', cols)
        rows = cur.execute('SELECT * FROM ' + tbl + ' LIMIT 2').fetchall()
        for r in rows:
            print('  sample:', [str(x)[:40] for x in r])
    except Exception as e:
        print('  ERR:', e)
    print()