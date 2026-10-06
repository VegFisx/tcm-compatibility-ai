"""ADMET 缓存备份 + 完整性校验
用法：D:\TCMAI\venv\Scripts\python.exe D:\TCMAI\scripts\backup_cache.py
"""
import pickle
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
CACHE = ROOT / "data" / "admet_cache.pkl"
BACKUP_DIR = ROOT / "backups" / "admet_cache"


def main():
    if not CACHE.exists():
        print(f"[X] 缓存不存在: {CACHE}")
        sys.exit(1)

    size_mb = CACHE.stat().st_size / 1024 / 1024
    print(f"[*] 源文件: {CACHE}")
    print(f"[*] 大小: {size_mb:.1f} MB")

    # 1. 加载校验
    print("[*] 加载校验中...")
    try:
        with open(CACHE, "rb") as f:
            data = pickle.load(f)
    except Exception as e:
        print(f"[X] 加载失败，文件可能已损坏: {e}")
        sys.exit(1)

    if isinstance(data, dict):
        print(f"[OK] 加载成功，dict，条目数: {len(data)}")
        for k in list(data.keys())[:3]:
            print(f"    样例 key={k!r} -> {type(data[k]).__name__}")
    elif hasattr(data, "__len__"):
        print(f"[OK] 加载成功，{type(data).__name__}，长度: {len(data)}")
    else:
        print(f"[OK] 加载成功，类型: {type(data).__name__}")

    # 2. 备份
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"admet_cache_{ts}.pkl"
    shutil.copy2(CACHE, backup)
    print(f"[OK] 已备份到: {backup}")

    # 3. 回读校验
    print("[*] 校验备份...")
    try:
        with open(backup, "rb") as f:
            data2 = pickle.load(f)
        assert len(data2) == len(data), "条数不一致"
        print(f"[OK] 备份校验通过，条数一致: {len(data2)}")
    except Exception as e:
        print(f"[X] 备份校验失败: {e}")
        sys.exit(1)

    print("\n完成。")


if __name__ == "__main__":
    main()