# 🐺 LLM Werewolf Arena | 多智能体异构大模型狼人杀沙盒

基于 Python 构建的 7 人局非完全信息博弈（Imperfect-Information Game）多智能体沙盒。本项目旨在探索和评估不同的大语言模型（LLMs）在复杂欺骗、逻辑推理与长期记忆管理等场景下的表现。

## ✨ 核心特性 (Core Features)

* 🤖 **异构大模型竞技场 (Heterogeneous Arena)：** 支持 DeepSeek, Qwen, Hunyuan, Doubao 等多个国内外顶尖模型的同台混合博弈。通过统一的 API Gateway 实现了模型的无缝切换与座次分配。
* 🛡️ **底层接口解耦与消息清洗 (Adapter Pattern)：** 针对不同厂商 API 对 `system` 提示词的严格程度差异，在 `llm_client` 层实现了优雅的“消息清洗器”。隔离了底层游戏引擎与外部大模型接口，保证了核心状态机的纯粹性。
* 🧠 **无损长文本记忆流 (Full Context Memory)：** 摒弃了传统的固定长度记忆截断，赋予 AI 玩家贯穿全局的上下文记忆能力，使其能够进行跨天数的逻辑回溯与盘问。
* 📊 **自动化消融评测引擎 (Automated Evaluator)：** 内置 `arena.py` 提供无头（Headless）批处理对战模式。支持自动化统计胜率、生成对局复盘日志，为算法表现提供量化指标。

## 📂 核心架构与文件结构

```text
├── game.py             # 核心游戏引擎与严格的状态机管理（白天/黑夜循环、投票结算）
├── game_objects.py     # OOP 设计的实体类（Player基类及各身份子类定义）
├── llm_client.py       # 大模型网关与请求发送器（内置自动重试与异构 API 兼容清洗机制）
├── prompts.py          # 角色系统提示词库（包含平民逻辑、狼人欺骗与夜间加密频道的 Prompt）
├── arena.py            # 批处理评测脚本，用于生成多局对抗的统计报告
├── app.py / play.py    # （可选）游戏启动入口 / 交互端
└── .env                # 环境变量配置（存放各家 API Key，已在 .gitignore 中忽略）

## 🚀 快速启动 (Quick Start)

### 1. 环境配置

强烈建议使用 Python 3.10+ 并在虚拟环境中运行本项目。

**克隆仓库并安装依赖：**
```bash
git clone [https://github.com/你的用户名/你的仓库名.git](https://github.com/你的用户名/你的仓库名.git)
cd 你的仓库名

# 创建并激活虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Windows 用户请使用 venv\Scripts\activate

# 安装核心依赖项
pip install -r requirements.txt
```

### 配置API密钥
在根目录创建 .env 文件，并根据你的异构模型选择填入对应的 API Keys（模板如下）：

```
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_BASE_URL=[https://api.deepseek.com](https://api.deepseek.com)
# 可选：配置其他厂商 API 以启动异构对战
QWEN_API_KEY=sk-xxxx
HUNYUAN_API_KEY=sk-xxxx
DOUBAO_API_KEY=xxxx-xxxx
```
