# TCM-ChemAI

中药配伍毒性预测系统 —— 基于 RDKit 反应规则与 ADMET 预测。

## 简介

预测中药配伍煎煮过程中的化学成分变化及毒性演化。

- 数据源：HERB（药材级）+ COCONUT（物种级）
- 反应预测：RDKit + 23 条 SMARTS 规则
- 毒性评估：admet-ai（hERG / AMES / ClinTox）
- 交互：LLM 自然语言问答（只做语言组织，不编化学数据）

## 主要发现

- 甘草对 4 个十八反配伍系统性减毒（ΔhERG -0.077 到 -0.103）
- 半夏+乌头是唯一煎煮增毒的十八反（ΔhERG +0.034）
- 减毒机制为产物修饰而非直接灭活

## 环境

- Python 3.12
- RDKit 2026.3.6+
- admet-ai 2.0.1+
- 详见 requirements.txt

## 安装

```bash
conda create -n tcmai python=3.12 -y
conda activate tcmai
pip install -r requirements.txt
```

## 数据准备

需自行下载（放到项目根目录）：

| 文件 | 来源 |
|---|---|
| tcm.db | HERB (http://herb.ac.cn/) |
| coconut.db | COCONUT |
| data/admet_cache.db | 跑 run_admet.py 生成 |

## 使用

```bash
# 单药对分析
python src/tcm_analyzer.py 附子,甘草

# 18 组批量
python src/batch_pairs.py

# LLM 问答
python src/llm_agent.py
python src/llm_agent.py "四逆汤的毒性有多大？"

# 方剂查询
python scripts/formula_lookup.py 四逆汤
```

## 引用

[待填 —— 论文发表后补]

## 许可证

MIT License. 详见 LICENSE。
