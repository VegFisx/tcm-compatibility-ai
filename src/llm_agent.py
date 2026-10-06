# -*- coding: utf-8 -*-
r"""
中药配伍 AI 自由问答

用法：
    python llm_agent.py "四逆汤的毒性有多大？"
    python llm_agent.py

功能：
- LLM 提取药材名/方剂名 → 程序调真实分析 → LLM 组织回答
- 方剂名走 apihz API 解析，自动选权威版本
- 剂量加权、多轮对话、拉丁名归一、missed 防错
- 替换语义（"元参换成玄参"）
- 级联反应：3 轮连续反应
- 自动保存：logs/qa_history/YYYY-MM-DD.txt（按天追加）
- 手动导出：交互模式输入 save [路径] 导出完整会话
"""
import os
import sys
import json
import re
import atexit
import requests
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\TCMAI")
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from db_utils import find_compounds, collect_compounds
from tcm_analyzer import check_toxicity, predict_reactions
from admet_cache import ADMETCache
from parse_peifang import parse_peifang
from dose_weights import compute_weights
from cascade_reactions import find_final_products

try:
    from openai import OpenAI
except ImportError:
    print("[ERR] 缺 openai 库。请跑：")
    print("  D:\\TCMAI\\venv\\Scripts\\pip.exe install openai python-dotenv requests")
    sys.exit(1)

API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY") or os.getenv("LLM_API_KEY")
BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("BASE_URL") or os.getenv("LLM_BASE_URL")
MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "deepseek-chat"

FORMULA_API = "https://cn.apihz.cn/api/jiankang/zyfj.php"
FORMULA_ID = os.getenv("APIHZ_ID") or "88888888"
FORMULA_KEY = os.getenv("APIHZ_KEY") or "88888888"

QA_HISTORY_DIR = ROOT / "logs" / "qa_history"
QA_EXPORTS_DIR = ROOT / "logs" / "qa_exports"

client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL or None)

CACHE = ADMETCache()


def _cleanup():
    for obj in (CACHE, client):
        try:
            obj.close()
        except Exception:
            pass


atexit.register(_cleanup)


SOURCE_PRIORITY = ["伤寒论", "金匮要略", "温病条辨", "太平惠民和剂局方",
                   "外台", "圣惠", "圣济总录", "普济方"]

PROCESS_PREFIX = ["炙", "炒", "焦", "煅", "生", "制", "炮", "熟",
                  "酒", "醋", "盐", "蜜", "姜", "麸", "土", "米"]

CASCADE_KEYWORDS = ["产物之间", "再反应", "二级", "多级", "继续反应",
                    "进一步反应", "反应链", "终产物", "最终产物",
                    "稳定", "平衡", "煎煮到底", "煎透", "反应到最后"]


# ============================================================
# 会话上下文
# ============================================================
class Conversation:
    def __init__(self, max_turns: int = 5):
        self.turns = []
        self.max_turns = max_turns

    def add(self, question: str, herbs: list, formula, answer: str):
        self.turns.append({
            "q": question,
            "herbs": list(herbs or []),
            "formula": formula,
            "answer": answer or "",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def context_str(self) -> str:
        if not self.turns:
            return ""
        lines = ["【之前的对话】"]
        for i, t in enumerate(self.turns, 1):
            lines.append(f"{i}. 用户问：{t['q']}")
            if t["herbs"]:
                lines.append(f"   涉及药材：{', '.join(t['herbs'])}")
            if t["formula"]:
                lines.append(f"   涉及方剂：{t['formula']}")
        return "\n".join(lines)

    def reset(self):
        self.turns = []

    def to_markdown(self) -> str:
        if not self.turns:
            return "# 会话导出\n\n（无内容）\n"
        lines = [
            "# 中药配伍 AI 问答 — 会话导出",
            "",
            f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**模型**: {MODEL}",
            f"**轮数**: {len(self.turns)}",
            "",
            "---",
            "",
        ]
        for i, t in enumerate(self.turns, 1):
            lines.append(f"## 第 {i} 轮 · {t.get('time', '')}")
            lines.append("")
            lines.append(f"**问**：{t['q']}")
            lines.append("")
            if t["herbs"]:
                lines.append(f"**涉及药材**：{'、'.join(t['herbs'])}")
                lines.append("")
            if t["formula"]:
                lines.append(f"**涉及方剂**：{t['formula']}")
                lines.append("")
            lines.append("**AI 回答**：")
            lines.append("")
            lines.append(t["answer"])
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def save_to(self, target: str = None) -> Path:
        QA_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        if not target:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = QA_EXPORTS_DIR / f"session_{ts}.txt"
        else:
            p = Path(target)
            if p.is_absolute():
                out = p
                out.parent.mkdir(parents=True, exist_ok=True)
            else:
                if not p.suffix:
                    p = p.with_suffix(".txt")
                out = QA_EXPORTS_DIR / p.name
                out.parent.mkdir(parents=True, exist_ok=True)

        out.write_text(self.to_markdown(), encoding="utf-8")
        return out


def _append_to_daily_log(question: str, answer: str,
                         herbs: list = None, formula: str = None):
    try:
        QA_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log = QA_HISTORY_DIR / f"{today}.txt"
        ts = datetime.now().strftime("%H:%M:%S")

        block = [f"\n## [{ts}] {question}\n"]
        if herbs:
            block.append(f"*涉及药材*: {'、'.join(herbs)}\n")
        if formula:
            block.append(f"*涉及方剂*: {formula}\n")
        block.append("\n" + (answer or "") + "\n")
        block.append("\n---\n")

        if not log.exists():
            header = f"# {today} · 问答记录\n\n---\n"
            log.write_text(header, encoding="utf-8")

        with log.open("a", encoding="utf-8") as f:
            f.write("\n".join(block))
    except Exception as e:
        print(f"[warn] 自动保存失败: {type(e).__name__}: {e}")


# ============================================================
# 方剂 API
# ============================================================
def _source_rank(chuchu: str) -> int:
    if not chuchu:
        return 999
    for i, s in enumerate(SOURCE_PRIORITY):
        if s in chuchu:
            return i
    return 500


def _normalize_herb(name: str) -> str:
    if not name:
        return name
    for p in PROCESS_PREFIX:
        if name.startswith(p) and len(name) > len(p):
            return name[len(p):]
    return name


def resolve_formula(name: str):
    try:
        r = requests.post(FORMULA_API,
                          data={"id": FORMULA_ID, "key": FORMULA_KEY,
                                "words": name, "page": 1},
                          timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"      [方剂 API 失败] {e}")
        return None, None, None

    if data.get("code") != 200:
        print(f"      [方剂 API 错误] code={data.get('code')} msg={data.get('msg')}")
        return None, None, None

    datas = data.get("datas") or []
    if not datas:
        return None, None, None

    exact = [d for d in datas if (d.get("name") or "").strip() == name]
    if exact:
        datas = exact

    datas.sort(key=lambda d: _source_rank(d.get("chuchu", "")))
    best = datas[0]

    items = parse_peifang(best.get("peifang") or "")
    if not items:
        return None, None, None

    raw_weights = compute_weights(items)

    herbs, weights = [], {}
    for it in items:
        raw_h = it["herb"]
        norm_h = _normalize_herb(raw_h)
        if not norm_h:
            continue
        if norm_h not in herbs:
            herbs.append(norm_h)
        weights[norm_h] = weights.get(norm_h, 0.0) + raw_weights.get(raw_h, 0.0)

    total_w = sum(weights.values())
    if total_w > 0:
        weights = {h: w / total_w for h, w in weights.items()}

    info = {
        "name": best.get("name"),
        "source": best.get("chuchu"),
        "raw": best.get("peifang"),
        "n_versions": len(datas),
    }
    return herbs, weights, info


# ============================================================
# 1. LLM 提取药材名 / 方剂名
# ============================================================
def extract_intent(question, conversation=None):
    ctx = conversation.context_str() if conversation else ""
    system_content = (
        '你是中药名识别助手。用户问中药配伍问题，'
        '你只输出 JSON：'
        '{"herbs": ["药名1", "药名2"], "formula": null, "replace": null}。\n'
        '规则：\n'
        '1) 如果用户提到的是中药方剂名（如四逆汤、小柴胡汤、六味地黄丸），'
        '   把方剂名放进 formula 字段，herbs 留空；\n'
        '2) 如果用户提到的是具体药材名（如附子、甘草），放进 herbs 数组；\n'
        '3) 两者都有则都填；\n'
        '4) 识别不出就 {"herbs": [], "formula": null, "replace": null}。\n'
        '5) 只输出中文药名。如果用户用了拉丁学名、英文名或拼音，'
        '   先转成对应的标准中文药名再输出。'
        '   Panax notoginseng=三七, Panax ginseng=人参, '
        '   Aconitum carmichaelii=附子, Glycyrrhiza uralensis=甘草, '
        '   Ephedra sinica=麻黄, Cinnamomum cassia=桂枝, '
        '   Rheum palmatum=大黄, Pinellia ternata=半夏, '
        '   Poria cocos=茯苓, Atractylodes macrocephala=白术, '
        '   Zingiber officinale=干姜/生姜, Paeonia lactiflora=白芍, '
        '   Scutellaria baicalensis=黄芩, Bupleurum chinense=柴胡。\n'
    )
    if ctx:
        system_content += (
            f"\n{ctx}\n\n"
            '【多轮对话处理】：\n'
            '6) 如果用户的问题是对上一轮的追问（如"那它的毒性呢？"、'
            '"附子呢？"、"这个方安全吗？"），且没有明说新的药材/方剂名，'
            '   就把上一轮涉及的 herbs / formula 重复填进当前 JSON；\n'
            '7) 如果用户明确提了新药材（如之前聊四逆汤，现在问"附子"），'
            '   只用新药材，不要继承旧的；\n'
            '8) 如果用户用了"换成""改为""替换""替代"等词，说明是替换语义：\n'
            '   - herbs 字段：填替换后的完整药材列表\n'
            '   - formula 字段：如果原方有名字，填方剂名\n'
            '   - replace 字段：填 {"from": "被替换的药", "to": "新药"}\n'
            '   例如：原方"四妙勇安汤"含金银花、元参、当归、甘草，'
            '   用户说"把元参换成玄参"，'
            '   应输出 {"herbs": ["金银花","玄参","当归","甘草"], '
            '"formula": "四妙勇安汤", "replace": {"from": "元参", "to": "玄参"}}；\n'
            '9) 优先用上下文里出现过的完整药名，不要简写。\n'
        )
    system_content += '没有替换时 replace 填 null。不要输出其他文字。'

    messages = [{"role": "system", "content": system_content}]
    messages.append({"role": "user", "content": question})

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        data = None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', text, re.S)
            if m:
                data = json.loads(m.group(0))
        if data:
            return (data.get("herbs") or [],
                    data.get("formula"),
                    data.get("replace"))
    except Exception as e:
        print(f"[LLM-ERR] 提取失败: {e}")
    return [], None, None


# ============================================================
# 2. 程序调真实分析
# ============================================================
def _herb_of(compound: dict) -> str:
    return (compound.get("source") or "").replace("(COCONUT)", "")


def analyze_herbs(herb_list, max_n=200, weights=None, cascade=False):
    uniq, missed = collect_compounds(herb_list, herb_limit=max_n,
                                     coconut_limit=1000, return_missed=True)
    toxic = [c for c in uniq if check_toxicity(c)]

    def _global_avg(metric):
        vals = []
        for c in uniq:
            rec = CACHE.get(c["smiles"])
            if rec and rec.get(metric) is not None:
                vals.append(float(rec[metric]))
        return round(sum(vals) / len(vals), 3) if vals else None

    def _weighted_avg(metric):
        if not weights:
            return _global_avg(metric)
        by_herb = defaultdict(list)
        for c in uniq:
            rec = CACHE.get(c["smiles"])
            if not rec or rec.get(metric) is None:
                continue
            by_herb[_herb_of(c)].append(float(rec[metric]))
        if not by_herb:
            return None
        num, den = 0.0, 0.0
        for h, vals in by_herb.items():
            avg_h = sum(vals) / len(vals)
            w = weights.get(h, 1.0)
            num += avg_h * w
            den += w
        return round(num / den, 3) if den > 0 else None

    compound_examples = []
    by_herb = defaultdict(list)
    for c in uniq:
        by_herb[_herb_of(c)].append(c)
    for h, items in by_herb.items():
        for c in items[:5]:
            compound_examples.append({
                "name": c.get("name", "?"),
                "smiles": c.get("smiles"),
                "cas_id": c.get("cas_id") or "未收录",
                "from_herb": h,
                "mw": c.get("mol_weight"),
                "type": "原成分",
            })

    cascade_result = None
    if cascade and uniq:
        cascade_result = find_final_products(uniq,
                                             max_rounds=8,
                                             frontier_limit=500,
                                             min_new=10)
        products = cascade_result["products"]
    else:
        products = predict_reactions(uniq) if uniq else []

    product_details = []
    seen_rxn = set()
    for p in products:
        rxn = p.get("rxn", "?")
        if rxn in seen_rxn:
            continue
        seen_rxn.add(rxn)
        product_details.append({
            "reaction": rxn,
            "from_compound": p.get("from_compound", "?"),
            "from_herb": p.get("from_herb", "?"),
            "formula": p.get("formula"),
            "smiles": p.get("smiles"),
            "mw": p.get("mw"),
            "cas_id": None,
            "type": "反应产物",
        })

    admet_n = sum(1 for c in uniq if CACHE.get(c["smiles"]))

    result = {
        "herbs": herb_list,
        "missed_herbs": missed,
        "compounds": len(uniq),
        "toxic_n": len(toxic),
        "toxic_examples": [c.get("name", "?") for c in toxic[:15]],
        "products": len(products),
        "compound_examples": compound_examples,
        "product_details": product_details,
        "admet_n": admet_n,
        "hERG": _weighted_avg("hERG"),
        "AMES": _weighted_avg("AMES"),
        "ClinTox": _weighted_avg("ClinTox"),
    }

    if cascade_result:
        result["cascade"] = {
            "rounds": cascade_result["rounds"],
            "converged": cascade_result["converged"],
            "round_stats": cascade_result["round_stats"],
            "total": cascade_result["total"],
        }

    if weights:
        result["weights"] = {h: round(w, 3) for h, w in weights.items()}
        result["hERG_unweighted"] = _global_avg("hERG")
        result["AMES_unweighted"] = _global_avg("AMES")
        result["ClinTox_unweighted"] = _global_avg("ClinTox")

    return result


# ============================================================
# 3. LLM 组织回答
# ============================================================
def generate_answer(question, data, formula_info=None, conversation=None):
    data_str = json.dumps(data, ensure_ascii=False, indent=2)
    formula_note = ""
    if formula_info:
        formula_note = (f"\n方剂识别：{formula_info['name']} — {formula_info['source']}"
                        f"\n原始配方：{formula_info['raw']}\n")

    ctx_note = ""
    if conversation and conversation.turns:
        ctx_note = f"\n{conversation.context_str()}\n"

    prompt = f"""用户问题：{question}
{ctx_note}{formula_note}
系统真实分析数据（JSON）：
{data_str}

请用中文简洁回答，要求：
1. 只基于上面数据，不要编造数字
2. 如果某指标为 null 请说"未预测"
3. 提毒性分子时用 toxic_examples 里的名字
4. 判断：hERG > 0.5 高风险，0.3-0.5 中等，< 0.3 较安全
5. 语气客观，像分析报告
6. 如果是方剂，回答开头点明方剂名和出处
7. 若数据里有 hERG_unweighted 字段，说明已按剂量加权；
   回答时以 hERG 为准，可顺便提未加权值作对照
8. 如果用户在追问（如"那XX呢"），回答时承接上下文，
   不要重复已说过的全部信息

【区分"原成分"与"反应产物"】：
9. 用户问"产生哪些化合物 / 煎煮生成什么 / 反应产物"时：
   → 从 product_details 里选 5 个（尽量覆盖不同 reaction 类型），
     逐条列出：反应类型、来源化合物、分子式、SMILES。
   → 产物是 RDKit 预测的，数据库中无 CAS，须注明"预测产物（无 CAS）"。
   → 不要用 compound_examples 充当产物。

10. 用户问"含哪些成分 / 有哪些化合物 / 原成分的 CAS"时：
    → 从 compound_examples 里选，逐条列：名称、CAS、SMILES、来源药材。
    → CAS 字段为"未收录"时照实说。

11. 用户问"配伍 / 共煎 会产生什么"时：
    → 优先按规则 9 处理（列产物），可补充说明产物源于哪些原成分。

12. 若某味药在数据库中无成分记录（如芒硝、石膏等无机药），
    说明其"煎煮条件下不参与有机反应"或"数据库无有机成分记录"。

【missed_herbs 处理】：
13. 若数据里 missed_herbs 非空，说明这些药材在数据库中无任何成分记录。
    回答时必须明确说明"XX 未在数据库中查到，未纳入本次分析"，
    列在回答开头或结尾的显著位置。
    不要假装分析过它，不要编造它的成分，也不要把它算进"共 N 味"里。

【级联反应（cascade）】：
14. 若数据里有 cascade 字段且非空：
    → cascade 是"3 轮连续反应"的产物集合，模拟煎煮时间内
      可完成的主要反应步数（非热力学平衡态）。
    → 回答时说明：经 3 轮模拟、累计产物 M 个、
      举 5 个代表性产物（覆盖不同 reaction 类型），
      注明"有限时间内的可达产物近似，非化学平衡态"。
    → 不要提"收敛""稳定态"这类词。

【表达方式】：
15. 不要直接念 JSON 字段名。用自然语言表达：
    "四味药均在库中查到" 而不是 "missed_herbs 为空"。
"""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system",
                 "content": "你是中医药化学分析助手。只基于给定数据分析，不编造。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM 回答失败] {type(e).__name__}: {e}"


# ============================================================
# 主流程
# ============================================================
def handle_question(question, conversation=None):
    if client is None:
        return ("[错误] 未配置 API Key。请在 D:\\TCMAI\\.env 里配置：\n"
                "  OPENAI_API_KEY=sk-xxxxxx\n"
                "  OPENAI_BASE_URL=https://api.deepseek.com/v1\n"
                "  OPENAI_MODEL=deepseek-chat")

    print("[1/4] LLM 识别意图（药材名 / 方剂名 / 替换）...")
    herbs, formula, replace = extract_intent(question, conversation=conversation)
    print(f"      → 药材={herbs}, 方剂={formula}, 替换={replace}")

    formula_info = None
    weights = None
    is_replace = bool(replace and replace.get("from") and replace.get("to"))

    if formula:
        print(f"[2/4] 查方剂「{formula}」...")
        f_herbs, f_weights, formula_info = resolve_formula(formula)
        if f_herbs:
            print(f"      → 选中「{formula_info['name']}」— {formula_info['source']}"
                  f"（共 {formula_info['n_versions']} 版本）")
            print(f"      → 方剂组成：{f_herbs}")

            if is_replace:
                from_h = replace["from"]
                to_h = replace["to"]
                if f_weights:
                    weights = dict(f_weights)
                    if from_h in weights:
                        weights[to_h] = weights.pop(from_h)
                        print(f"      → 权重映射：{from_h}({f_weights.get(from_h, 0):.3f}) "
                              f"→ {to_h}")
                    weights = {h: w for h, w in weights.items() if h in herbs}
                    tw = sum(weights.values())
                    if tw > 0:
                        weights = {h: w / tw for h, w in weights.items()}
                    wstr = ", ".join(f"{h}={w:.3f}" for h, w in weights.items())
                    print(f"      → 剂量权重：{wstr}")
                print(f"      → 替换模式：不合并方剂药材，只使用 LLM 提取的列表")
            else:
                if f_weights:
                    weights = f_weights
                    wstr = ", ".join(f"{h}={w:.3f}" for h, w in weights.items())
                    print(f"      → 剂量权重：{wstr}")
                herbs = herbs + [h for h in f_herbs if h not in herbs]
        else:
            print(f"      → 未查到方剂「{formula}」")

    if not herbs:
        answer = "抱歉，没识别出药材名或方剂名。请用'附子+甘草'或'四逆汤'格式提问。"
        if conversation is not None:
            conversation.add(question, [], None, answer)
        _append_to_daily_log(question, answer, [], formula)
        return answer

    need_cascade = any(kw in question for kw in CASCADE_KEYWORDS)
    print(f"[3/4] 跑真实分析（{len(herbs)} 味）"
          f"{' · 多级反应' if need_cascade else ''}...")
    data = analyze_herbs(herbs, weights=weights, cascade=need_cascade)

    print(f"      → 成分 {data['compounds']} / 毒性 {data['toxic_n']} / "
          f"产物 {data['products']}")
    if data.get("missed_herbs"):
        print(f"      → [警告] 未查到成分的药材: {data['missed_herbs']}")
    if need_cascade and data.get("cascade"):
        c = data["cascade"]
        stats = " → ".join(f"R{s['round']}:{s['new']}" for s in c["round_stats"])
        print(f"      → 级联: {stats}")
    if weights:
        print(f"      → hERG: {data['hERG_unweighted']} (未加权) → "
              f"{data['hERG']} (剂量加权)")
    else:
        print(f"      → hERG {data['hERG']} / AMES {data['AMES']} / "
              f"ClinTox {data['ClinTox']}")

    print("[4/4] LLM 组织回答...")
    answer = generate_answer(question, data, formula_info, conversation=conversation)

    if conversation is not None:
        conversation.add(question, herbs, formula, answer)

    _append_to_daily_log(question, answer, herbs, formula)

    return answer


def _run_once(question):
    ans = handle_question(question)
    print(f"\n【AI 回答】\n{ans}")


def _run_interactive():
    print("=" * 60)
    print("中药配伍 AI 自由问答（交互模式 · 支持多轮对话）")
    print("=" * 60)
    print(f"模型: {MODEL}")
    print(f"接口: {BASE_URL or 'OpenAI 官方'}")
    print(f"自动保存: {QA_HISTORY_DIR}")
    print()
    print("示例：")
    print("  · 四逆汤的毒性有多大？")
    print("  · 那它的主要成分呢？                ← 追问")
    print("  · 附子+甘草配伍毒不毒？")
    print("  · 四妙勇安汤的成分分析")
    print("  · 把元参换成玄参再跑一遍            ← 替换")
    print()
    print("命令：")
    print("  · save                 导出完整会话到 logs/qa_exports/")
    print("  · save 论文表格         导出到 logs/qa_exports/论文表格.txt")
    print("  · save D:\\某处\\x.txt   导出到指定路径")
    print("  · reset / 清空           清空对话历史")
    print("  · q / 退出               退出")
    print()

    conv = Conversation()
    while True:
        try:
            q = input("你问 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not q:
            continue
        if q.lower() in ("q", "quit", "exit", "退出"):
            break
        if q.lower() in ("reset", "清空", "重置"):
            conv.reset()
            print("[已清空对话历史]\n")
            continue
        if q.lower() in ("save", "导出", "保存") or \
           q.lower().startswith("save ") or q.lower().startswith("导出 "):
            args = q.split(maxsplit=1)
            target = args[1].strip() if len(args) > 1 else None
            try:
                out = conv.save_to(target)
                print(f"[已导出] {out}\n")
            except Exception as e:
                print(f"[导出失败] {type(e).__name__}: {e}\n")
            continue

        try:
            ans = handle_question(q, conversation=conv)
            print(f"\n【AI 回答】\n{ans}\n")
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}\n")


def main():
    if client is None:
        print("[ERR] 没找到 API Key。请在 D:\\TCMAI\\.env 里配置：")
        print("  OPENAI_API_KEY=sk-xxxxxx")
        print("  OPENAI_BASE_URL=https://api.deepseek.com/v1")
        print("  OPENAI_MODEL=deepseek-chat")
        sys.exit(1)

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        try:
            _run_once(question)
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}")
            sys.exit(1)
        return

    _run_interactive()


if __name__ == "__main__":
    main()