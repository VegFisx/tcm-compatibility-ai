# -*- coding: utf-8 -*-
r"""
别名 → 规范名 映射表构建

数据源优先级（高 → 低）：
1. MANUAL（手工整理，最高优先级）
2. NTU《中文药名同义词表》（50607 条，来自四部权威辞典）
3. tcm.db 的 herbs.alias 字段（自动提取，兜底）

冲突处理：
- 同一别名对应多个规范名时：
  a) 优先选 tcm.db 里存在的规范名
  b) 其次选出现次数多的

输出：data/herb_aliases_map.json
"""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(r"D:\TCMAI")
DB = ROOT / "tcm.db"
XLSX = ROOT / "data" / "ChineseDrugEthnonymsSynonymyTable.xlsx"
OUT = ROOT / "data" / "herb_aliases_map.json"

# 手工整理（最高优先级，覆盖自动结果）
MANUAL = {
    # 高频别名
    "大茴香": "八角茴香",
    "地丁": "紫花地丁",
    "土牛膝": "牛膝",
    "土精": "人参",
    "山精": "白术",
    "山姜": "白术",
    "黄参": "人参",
    "血参": "人参",
    "红根": "丹参",
    "紫丹参": "丹参",
    "赤参": "丹参",
    "奔马草": "丹参",
    "木羊乳": "丹参",
    "靠山红": "丹参",
    "逐马": "玄参",
    "鹿肠": "玄参",
    "水萝卜": "玄参",
    "地骨": "地骨皮",
    "地节": "地骨皮",
    "地参": "知母",
    "穿地龙": "知母",
    "野蓼": "知母",
    "大麻子": "火麻仁",
    "地葵": "地肤子",
    "玉椒": "胡椒",
    "蛤蒌": "荜茇",
    "蜜香": "木香",
    "萎蕤": "玉竹",
    "黄脚鸡": "玉竹",
    "香白芷": "白芷",
    "马蓟": "大蓟",
    "田七": "三七",
    "红蓝花": "红花",
    "蓝叶": "大青叶",
    "通大海": "胖大海",
    "铁扇子": "桑叶",
    "鹭鸶花": "金银花",
    "白头公": "白头翁",
    "奶汁草": "蒲公英",
    "黄狗头": "蒲公英",
    "猫儿眼": "甘遂",
    "头痛花": "芫花",
    "紫金花": "芫花",
    "闷头花": "芫花",
    "野芋头": "天南星",
    "蛇芋": "天南星",
    "麻芋子": "白附子",
    "三步跳": "半夏",
    "地雷公": "半夏",
    "四棱草": "益母草",
    "野油麻": "益母草",
    "水香": "佩兰",
    "省头草": "佩兰",
    "香草": "佩兰",
    "排香草": "藿香",
    "野藿香": "藿香",
    "鱼香": "藿香",
    "南薄荷": "薄荷",
    "土薄荷": "薄荷",
    "野薄荷": "薄荷",
    "接骨丹": "续断",
    "接骨草": "续断",
    "灯笼果": "金樱子",
    "蜂糖罐": "金樱子",
    "细草": "细辛",
    "铃铛花": "细辛",
    "百枝": "防风",
    "屏风": "防风",
    "仙人衣": "蝉蜕",
    "猪母菜": "马齿苋",
    "狮子草": "马齿苋",
    "蛇草": "徐长卿",
    "白花草": "墨旱莲",
    "黑头草": "墨旱莲",
    "水葵花": "墨旱莲",
    "木蜜": "大枣",
    "泽芝": "泽泻",
    "水麻叶": "藿香",
    "鸡骨升麻": "升麻",
    # 常用简称
    "生地": "生地黄",
    "熟地": "熟地黄",
    "云苓": "茯苓",
    "橘皮": "陈皮",
    "广皮": "陈皮",
    "川军": "大黄",
    "别甲": "鳖甲",
    "首乌": "何首乌",
    "元参": "玄参",
    "怀山药": "山药",
    "淮山": "山药",
}


def load_from_excel():
    """读 NTU 表 → {别名: {规范名: 出现次数}}"""
    print(f"读 {XLSX.name} ...")
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    ws = wb.active
    result = defaultdict(lambda: defaultdict(int))
    rows = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        # 列: PrimaryDrugNameNo., PrimaryDrugName, DictionarySource, AlternateName, Remarks
        if len(row) < 4:
            continue
        primary, alt = row[1], row[3]
        if not primary or not alt:
            continue
        primary = str(primary).strip()
        alt = str(alt).strip()
        if not primary or not alt:
            continue
        result[alt][primary] += 1
        rows += 1
    wb.close()
    print(f"  {rows} 行 → {len(result)} 个不同别名")
    return result


def load_from_tcmdb():
    """读 tcm.db → {别名: {规范名: 出现次数}}"""
    print(f"读 {DB.name} ...")
    c = sqlite3.connect(str(DB))
    result = defaultdict(lambda: defaultdict(int))
    all_names = set()
    for name, alias in c.execute("SELECT name_cn, alias FROM herbs"):
        all_names.add(name)
        if not alias:
            continue
        for a in alias.split(";"):
            a = a.strip()
            if not a or a == name:
                continue
            result[a][name] += 1
    c.close()
    print(f"  {len(result)} 个不同别名，库内 {len(all_names)} 味药")
    return result, all_names


def pick_canonical(candidates: dict, all_names: set):
    """
    从多个候选中选一个规范名。
    优先：tcm.db 里存在的 > 出现次数多的 > 字典序（保底确定性）
    """
    items = list(candidates.items())

    # 优先选库内存在的
    in_db = [(n, c) for n, c in items if n in all_names]
    if in_db:
        items = in_db

    # 按出现次数降序，次数相同按字典序
    items.sort(key=lambda x: (-x[1], x[0]))
    return items[0][0]


def main():
    # 1. 读 Excel
    excel_map = load_from_excel()

    # 2. 读 tcm.db
    tcmdb_map, all_names = load_from_tcmdb()

    # 3. 合并（Excel 优先，tcm.db 兜底）
    print("\n合并 ...")
    merged = defaultdict(lambda: defaultdict(int))
    for alias, cands in tcmdb_map.items():
        for name, cnt in cands.items():
            merged[alias][name] += cnt
    for alias, cands in excel_map.items():
        for name, cnt in cands.items():
            # Excel 的计数乘以 2，让它在冲突时优先
            merged[alias][name] += cnt * 2

    # 4. 最终映射
    final = {}
    conflicts_resolved = 0
    skipped_is_name = 0
    total_alias = len(merged)

    for alias, cands in merged.items():
        # 别名本身就是规范名 → 跳过
        if alias in all_names:
            skipped_is_name += 1
            continue
        if len(cands) > 1:
            conflicts_resolved += 1
        final[alias] = pick_canonical(cands, all_names)

    # 5. 手工映射覆盖
    for k, v in MANUAL.items():
        final[k] = v

    # 6. 保存
    print(f"\n合并结果:")
    print(f"  总别名: {total_alias}")
    print(f"  跳过（别名是规范名）: {skipped_is_name}")
    print(f"  冲突已自动解决: {conflicts_resolved}")
    print(f"  最终映射条目: {len(final)}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8"
    )
    print(f"\n已保存: {OUT}")

    # 抽查
    print("\n=== 抽查 ===")
    for k in ["元参", "生地", "熟地", "怀山药", "川军", "云苓",
              "大茴香", "地丁", "土牛膝", "田七", "红蓝花"]:
        print(f"  {k} → {final.get(k, '(未收录)')}")


if __name__ == "__main__":
    main()