# -*- coding: utf-8 -*-
"""列出 D:\TCMAI 当前目录结构"""
from pathlib import Path

ROOT = Path(r"D:\TCMAI")

# 忽略的目录/后缀
IGNORE_DIRS = {"venv", "__pycache__", ".git", "build", ".idea", ".vscode"}
IGNORE_SUFFIX = {".pyc", ".pyo"}

def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def walk(path, prefix="", depth=0, max_depth=3):
    if depth > max_depth:
        return
    try:
        items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
    except PermissionError:
        return

    for item in items:
        if item.name in IGNORE_DIRS:
            continue
        if item.suffix in IGNORE_SUFFIX:
            continue

        if item.is_dir():
            # 统计目录大小 + 文件数
            n_files = 0
            total = 0
            for p in item.rglob("*"):
                if p.is_file() and p.suffix not in IGNORE_SUFFIX:
                    if any(ig in p.parts for ig in IGNORE_DIRS):
                        continue
                    n_files += 1
                    try:
                        total += p.stat().st_size
                    except OSError:
                        pass
            print(f"{prefix}[DIR]  {item.name}/  "
                  f"({n_files} files, {human_size(total)})")
            walk(item, prefix + "  ", depth + 1, max_depth)
        else:
            try:
                size = item.stat().st_size
            except OSError:
                size = 0
            print(f"{prefix}       {item.name}  ({human_size(size)})")

print(f"=== {ROOT} 目录结构 ===\n")
walk(ROOT)