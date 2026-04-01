import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from mentor.llm_config import get_mentor_llm
from mentor.schemas import SecretaryLedger

SECRETARY_PROMPT = """
你是一个极其严谨的狼人杀对局信息提取系统（Secretary Agent）。
你的唯一任务是阅读公共聊天记录（包含玩家发言与系统广播的投票记录），并将其转化为结构化的 JSON 记账单。

【强制提取原则】(违背将导致系统崩溃)
1. 【最高优先级：票型记录】：聊天记录中包含系统广播的投票动作（如“X号玩家投票放逐Y号”或“X号玩家选择弃票”）。这是狼人杀中最核心的事实！你必须将每一个人的投票动作单独提取为一条记录（例如 action_type 设为 "vote" 或对应动作，并明确 target_player）。绝不能遗漏任何一票！
2. 原子化拆分（极其重要）：如果玩家的发言包含“跳身份”和“对别人采取动作”，必须强制拆分为多条独立的记录！
   - 例如发言：“我跳预言家，昨晚查了4号是好人”。
   - 必须拆分为：记录A (action_type="claim", claimed_role="预言家", target_player=null)，以及记录B (action_type="support", target_player=4, claimed_role="预言家")。绝对不能揉在一起！
3. 身份状态贯穿：如果一个玩家在发言中表明了身份，那么他在本轮提取的所有动作记录中，`claimed_role` 字段都必须完整填写该身份，绝对不允许出现 null！
4. 去除废话：忽略单纯的情绪宣泄、无意义的闲聊。
5. 绝对中立：只记录“谁说了什么”和“谁投了谁”，绝对不要去判断他们说的是真是假。
6. 核心矛盾：用最精简的一两句话概括当前场上最大的争议点，以及最终的投票倒向。

请仔细阅读记录，并严格按照格式输出。
{format_instructions}
"""

def secretary_extraction_node(state: dict) -> dict:
    chat_history = state.get("short_term_memory", "")
    current_day = state.get("current_day", 1)
    
    if not chat_history:
        print("[Secretary Agent] No chat history provided. Skipping extraction.")
        return {"episodic_memory": None}

    # 1. 实例化 LLM 
    # 【进阶建议】：如果你想省钱，这里未来可以把 get_mentor_llm 换成豆包 (Doubao) 等更便宜的模型实例！
    llm = get_mentor_llm(temperature=0.0).bind(
        response_format={"type": "json_object"}
    )
    
    # 2. 初始化 Pydantic 解析器
    parser = PydanticOutputParser(pydantic_object=SecretaryLedger)

    # 3. 构建提示词
    prompt = ChatPromptTemplate.from_messages([
        ("system", SECRETARY_PROMPT),
        ("human", "当前天数：第 {current_day} 天\n\n【公共聊天与投票记录】\n{chat_history}")
    ])

    # 4. 组装 LCEL 链
    chain = prompt | llm | parser
    
    print("\n[Secretary Agent] Reading chat history and extracting ledger...")
    try:
        # 执行信息提取
        result = chain.invoke({
            "current_day": current_day,
            "chat_history": chat_history,
            "format_instructions": parser.get_format_instructions()
        })
        
        print(f"├─ 提取关键动作数: {len(result.key_actions)}")
        print(f"└─ 核心矛盾概括: {result.main_conflict}")
        
        # 将结构化的数据转化为普通的 Python 字典，填入全局状态的 episodic_memory 中
        return {"episodic_memory": result.model_dump()}
        
    except Exception as e:
        print(f"[Secretary Agent] Extraction failed: {e}")
        # 容错兜底：即使提取失败，也不能让整个系统崩溃
        return {"episodic_memory": None}

if __name__ == "__main__":
    # 本地极速测试入口
    mock_chat = """
    2号玩家：我是好人，昨晚啥也没看见。我觉得1号发言有点心虚，大家盯紧他。
    3号玩家：我是预言家，昨晚查了4号，是个好人。我觉得2号踩1号毫无逻辑，2号大概率是狼。
    """
    mock_state = {
        "current_day": 1,
        "short_term_memory": mock_chat
    }
    
    print("Running Secretary Node local test...")
    updated_state = secretary_extraction_node(mock_state)
    print("\n--- 最终生成的记账单 ---")
    import json
    print(json.dumps(updated_state["episodic_memory"], indent=2, ensure_ascii=False))