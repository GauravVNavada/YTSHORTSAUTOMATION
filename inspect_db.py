import sqlite3

conn = sqlite3.connect('data/sheets_cache.db')
conn.row_factory = sqlite3.Row

print("=== TABLES ===")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    count = conn.execute(f'SELECT COUNT(*) FROM "{t["name"]}"').fetchone()[0]
    print(f"  {t['name']}: {count} rows")

print("\n=== GENRE_CONFIG ===")
rows = conn.execute("SELECT * FROM genre_config").fetchall()
for r in rows:
    print(dict(r))

print("\n=== GENRES (first 5) ===")
try:
    rows = conn.execute("SELECT * FROM genres LIMIT 5").fetchall()
    for r in rows:
        print(dict(r))
except:
    print("No 'genres' table found")

print("\n=== ALL TABLE SCHEMAS ===")
for t in tables:
    schema = conn.execute(f"PRAGMA table_info('{t['name']}')").fetchall()
    cols = [f"{s['name']}({s['type']})" for s in schema]
    print(f"  {t['name']}: {', '.join(cols)}")

conn.close()
