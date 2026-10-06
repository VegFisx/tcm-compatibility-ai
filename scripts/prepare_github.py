# -*- coding: utf-8 -*-
"""生成 GitHub 上传目录（排除法）"""
import shutil
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
OUT = ROOT / "docs" / "github_upload" / "tcm-compatibility-ai"

SKIP_DIRS = {"venv", "backups", "archive", "build", "dist",
             "__pycache__", ".git", ".vscode", ".idea", "tools"}
SKIP_SUFFIX = {".db", ".pkl", ".log", ".pyc", ".db-wal", ".db-shm"}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    n = 0

    # 复制 src 和 scripts（整目录，排除 __pycache__）
    for sub in ["src", "scripts"]:
        src_dir = ROOT / sub
        dst_dir = OUT / sub
        for p in src_dir.rglob("*"):
            if not p.is_file():
                continue
            if "__pycache__" in p.parts:
                continue
            if p.suffix in SKIP_SUFFIX:
                continue
            rel = p.relative_to(src_dir)
            dst = dst_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            n += 1
        print(f"复制 {sub}/ 完成")

    # 复制顶层 .txt
    for p in ROOT.glob("*.txt"):
        shutil.copy2(p, OUT / p.name)
        n += 1

    # 复制数据表
    extras = [
        ("data/herb_aliases.json", "data/herb_aliases.json"),
        ("data/herb_aliases_map.json", "data/herb_aliases_map.json"),
        ("logs/batch_groups.csv", "results/batch_groups.csv"),
        ("docs/reports/admet_products_all_summary.csv",
         "results/admet_products_all_summary.csv"),
    ]
    for src_rel, dst_rel in extras:
        src = ROOT / src_rel
        if not src.exists():
            print(f"跳过: {src_rel}")
            continue
        dst = OUT / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        n += 1
        print(f"复制: {src_rel}")

    # 复制图
    fig_dir = OUT / "docs" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    for p in (ROOT / "docs" / "figures").glob("*.png"):
        shutil.copy2(p, fig_dir / p.name)
        n += 1

    print(f"\n完成！共 {n} 个文件")
    print(f"位置: {OUT}")


if __name__ == "__main__":
    main()