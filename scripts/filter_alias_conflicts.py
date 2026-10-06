# -*- coding: utf-8 -*-
r"""
从 969 个冲突里筛选真正需要人工处理的。

排除两类：
1. 别名本身是 herbs.name_cn 里的一条（用户输入直接命中，不需要映射）
2. 冲突不涉及常用药
"""
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
DB = ROOT / "tcm.db"
OUT = ROOT / "logs" / "alias_conflicts_real.txt"

# 常用药名单（可自行扩充）
COMMON_HERBS = set("""
甘草 附子 干姜 生姜 桂枝 麻黄 芍药 白芍 赤芍 大枣 人参 党参 白术 茯苓 当归
川芎 熟地黄 生地黄 黄芪 山药 山茱萸 牡丹皮 泽泻 柴胡 黄芩 黄连 黄柏 大黄
芒硝 厚朴 枳实 枳壳 半夏 陈皮 橘皮 杏仁 桔梗 前胡 贝母 知母 石膏 麦冬 天冬
五味子 枸杞子 菊花 金银花 连翘 薄荷 荆芥 防风 羌活 独活 细辛 白芷 苍术
玄参 麦门冬 天花粉 葛根 升麻 牛蒡子 蝉蜕 桑叶 桑白皮 地骨皮 丹皮
桃仁 红花 丹参 益母草 牛膝 川牛膝 怀牛膝 乳香 没药 三七 蒲黄 五灵脂
乌头 草乌 川乌 肉桂 吴茱萸 花椒 丁香 小茴香 八角茴香 木香 砂仁
白豆蔻 藿香 佩兰 天南星 白附子 竹茹 瓜蒌
酸枣仁 柏子仁 远志 龙骨 牡蛎 磁石 五味子 山茱萸 覆盆子 金樱子
阿胶 鹿茸 龟板 鳖甲 何首乌 龙眼肉
石斛 玉竹 黄精 百合 女贞子 墨旱莲 桑椹 沙参 西洋参
牛黄 羚羊角 大青叶 板蓝根 蒲公英 白头翁 马齿苋 败酱草 鱼腥草
火麻仁 郁李仁 甘遂 大戟 芫花 巴豆
猪苓 薏苡仁 车前子 滑石 木通 通草
高良姜 胡椒 荜茇
""".split())


def main():
    c = sqlite3.connect(str(DB))
    cur = c.cursor()

    all_names = {r[0] for r in cur.execute("SELECT name_cn FROM herbs")}

    alias_to_names = defaultdict(set)
    for name, alias in cur.execute("SELECT name_cn, alias FROM herbs"):
        if not alias:
            continue
        for a in alias.split(";"):
            a = a.strip()
            if not a or a == name:
                continue
            alias_to_names[a].add(name)

    conflicts = {a: names for a, names in alias_to_names.items() if len(names) > 1}

    # 1) 排除"别名本身是标准名"的
    real_conflicts = {a: n for a, n in conflicts.items() if a not in all_names}
    auto_filtered = len(conflicts) - len(real_conflicts)

    # 2) 只留涉及常用药的
    common_conflicts = {}
    for alias, names in real_conflicts.items():
        involved = {alias} | names
        if involved & COMMON_HERBS:
            common_conflicts[alias] = names

    print(f"总冲突: {len(conflicts)}")
    print(f"  自动过滤（别名是标准名）: {auto_filtered}")
    print(f"  剩余真实冲突: {len(real_conflicts)}")
    print(f"  其中涉及常用药: {len(common_conflicts)}\n")

    lines = [f"# 别名冲突清单（真正需要人工处理）\n",
             f"总数: {len(common_conflicts)}\n\n",
             "=" * 60 + "\n"]
    for alias in sorted(common_conflicts):
        names = sorted(common_conflicts[alias])
        lines.append(f"{alias}  →  {names}\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"已保存: {OUT}\n")

    print("=== 全部需要人工处理的 ===")
    for alias in sorted(common_conflicts):
        names = sorted(common_conflicts[alias])
        print(f"  {alias}  →  {names}")

    c.close()


if __name__ == "__main__":
    main()