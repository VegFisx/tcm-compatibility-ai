# -*- coding: utf-8 -*-
"""解析 API 返回的 peifang 字段 → [{"herb":..., "dose":..., "process":...}]
用法：
    python parse_peifang.py
    python parse_peifang.py "甘草2两（炙），干姜1两半，附子1枚（生用，去皮，破8片）。"
"""
import re
import sys

UNITS = r"两|钱|分|枚|升|合|斤|克|片|个|条|寸|粒|只|束|把|撮|盏|杯|碗"
NUM = r"[0-9０-９一二三四五六七八九十百]+"

# 剂量：数字+单位(+半) 或 半+单位
DOSE_RE = re.compile(rf"(?:{NUM}(?:{UNITS})(?:半)?|半(?:{UNITS}))")


def parse_peifang(text: str) -> list:
    if not text:
        return []

    # 1. 保护括号内容（切分时不切括号内）
    hold = {}

    def _protect(m):
        key = f"\x00{len(hold)}\x00"
        hold[key] = m.group(0)
        return key

    text = re.sub(r"[（(][^）)]*[）)]", _protect, text)

    # 2. 按标点切分
    parts = re.split(r"[，,、；;。]", text)

    results = []
    for p in parts:
        for k, v in hold.items():
            p = p.replace(k, v)
        p = p.strip()
        if not p:
            continue

        # 3. 提炮制（括号内容），并从原串去掉
        process_list = re.findall(r"[（(]([^）)]*)[）)]", p)
        process = "，".join(process_list) if process_list else None
        clean = re.sub(r"[（(][^）)]*[）)]", "", p).strip()

        # 4. 在去掉括号的串里找剂量
        m = DOSE_RE.search(clean)
        if m:
            herb = clean[:m.start()].strip()
            dose = m.group(0)
            tail = clean[m.end():].strip()
            if tail:
                process = f"{tail}，{process}" if process else tail
        else:
            herb = clean
            dose = None

        if herb:
            results.append({
                "herb": herb, "dose": dose, "process": process, "raw": p,
            })

    return results


def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = "甘草2两（炙），干姜1两半，附子1枚（生用，去皮，破8片）。"

    print(f"输入: {text}\n")
    for i, item in enumerate(parse_peifang(text), 1):
        print(f"[{i}] 药名={item['herb']!r}  剂量={item['dose']!r}  炮制={item['process']!r}")


if __name__ == "__main__":
    main()