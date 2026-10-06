# D:\TCMAI\scripts\crawl\check_alive.py
import os
import time
import sqlite3
import subprocess

LOG = r"D:\TCMAI\logs\crawl.log"
DB = r"D:\TCMAI\tcm.db"

def log_size():
    try:
        return os.path.getsize(LOG)
    except FileNotFoundError:
        return None

def db_done():
    try:
        conn = sqlite3.connect(DB, timeout=5)
        n = conn.execute("SELECT COUNT(*) FROM crawl_progress WHERE status='done'").fetchone()[0]
        conn.close()
        return n
    except Exception as e:
        return f"错误：{e}"

def python_procs():
    try:
        out = subprocess.check_output(
            ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine"],
            text=True, errors="ignore"
        )
        return [l.strip() for l in out.splitlines() if "crawl_herb_relations" in l]
    except Exception:
        return []

print("=== 第 1 次采样 ===")
size1 = log_size()
done1 = db_done()
print(f"日志大小: {size1}")
print(f"crawl_progress.done: {done1}")
print(f"运行中的爬虫进程: {python_procs()}")

print("\n等待 15 秒...")
time.sleep(15)

print("\n=== 第 2 次采样 ===")
size2 = log_size()
done2 = db_done()
print(f"日志大小: {size2}")
print(f"crawl_progress.done: {done2}")
print(f"运行中的爬虫进程: {python_procs()}")

print("\n=== 结论 ===")
if python_procs() and (size1 != size2 or done1 != done2):
    print("✅ 爬虫活着，正常工作中")
elif python_procs() and size1 == size2 and done1 == done2:
    print("⚠️ 进程在，但没输出也没写库，可能卡住了")
elif not python_procs():
    print("❌ 爬虫已停止，需要重启")