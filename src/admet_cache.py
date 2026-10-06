# -*- coding: utf-8 -*-
"""ADMET 预测缓存：InChIKey → 属性字典

底层存储：SQLite（data/admet_cache.db）
- 每行 = 一个 InChIKey + 一个 JSON blob
- 用 JSON 而非 100 列宽表：admet-ai 以后加字段不用改 schema
- 写入即时提交（WAL 模式），进程崩溃不会损坏已有数据

兼容层：
- 对外接口（get/has/put/save/size/.data）与旧 pickle 版完全一致
- 首次运行若 .db 为空且旧 .pkl 存在，自动迁移
"""
import json
import pickle
import sqlite3
from pathlib import Path
from typing import Dict, Optional

from rdkit import Chem

ROOT = Path(r"D:\TCMAI")
DB_FILE = ROOT / "data" / "admet_cache.db"
PKL_FILE = ROOT / "data" / "admet_cache.pkl"   # 旧格式，仅作迁移源
CACHE_FILE = DB_FILE                            # 向后兼容别名


def smiles_key(smiles: str) -> Optional[str]:
    """SMILES → InChIKey（跨运行稳定）"""
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    try:
        return Chem.MolToInchiKey(m)
    except Exception:
        return None


class ADMETCache:
    def __init__(self, cache_file=DB_FILE):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, dict] = {}

        self.conn = sqlite3.connect(str(self.cache_file))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS admet ("
            "  inchikey TEXT PRIMARY KEY,"
            "  data TEXT NOT NULL"
            ")"
        )
        self.conn.commit()

        self._load()

    def _load(self):
        for k, blob in self.conn.execute("SELECT inchikey, data FROM admet"):
            try:
                self.data[k] = json.loads(blob)
            except Exception:
                pass

        # 首次运行：.db 为空 + 旧 .pkl 存在 → 自动迁移
        if not self.data and PKL_FILE.exists() and PKL_FILE != self.cache_file:
            self._migrate_from_pkl()

    def _migrate_from_pkl(self):
        print(f"[cache] 从旧 pickle 迁移: {PKL_FILE}")
        try:
            with open(PKL_FILE, "rb") as f:
                old = pickle.load(f)
        except Exception as e:
            print(f"[cache warn] pickle 读取失败，跳过迁移: {e}")
            return
        if not isinstance(old, dict):
            print("[cache warn] pickle 内容不是 dict，跳过迁移")
            return
        rows = [(k, json.dumps(v, ensure_ascii=False)) for k, v in old.items()]
        self.conn.executemany(
            "INSERT OR REPLACE INTO admet (inchikey, data) VALUES (?, ?)", rows
        )
        self.conn.commit()
        self.data = dict(old)
        print(f"[cache] 迁移完成: {len(rows)} 条 → {self.cache_file}")

    def save(self):
        """全量同步 self.data 到 SQLite（兜底：防止外部直接改 .data）"""
        rows = [(k, json.dumps(v, ensure_ascii=False)) for k, v in self.data.items()]
        self.conn.executemany(
            "INSERT OR REPLACE INTO admet (inchikey, data) VALUES (?, ?)", rows
        )
        self.conn.commit()

    def get(self, smiles: str) -> Optional[dict]:
        k = smiles_key(smiles)
        return self.data.get(k) if k else None

    def has(self, smiles: str) -> bool:
        return self.get(smiles) is not None

    def put(self, smiles: str, result: dict):
        k = smiles_key(smiles)
        if not k:
            return
        self.data[k] = result
        self.conn.execute(
            "INSERT OR REPLACE INTO admet (inchikey, data) VALUES (?, ?)",
            (k, json.dumps(result, ensure_ascii=False)),
        )
        self.conn.commit()

    def size(self) -> int:
        return len(self.data)

    def close(self):
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass