import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from mentor.llm_config import get_mentor_llm
from mentor.schemas import BossRoutingDecision

SUPERVISOR_PROMPT = """
你是一个多智能体狼人杀导师团队的最高主管。你是唯一直接与人类玩家对话的 AI。

【狼人杀绝对术语与价值观纠偏（极其重要）】
1. 投票 = 处决/放逐：当玩家问“我应该投谁”或“票谁”时，意思是“我应该把谁投票驱逐出局（因为怀疑他是狼）”，绝对不是“支持”或“保护”！
2. 踩 = 怀疑；保 = 信任/发好人卡。
3. 你的所有战术建议必须基于“如何帮玩家所在的阵营赢”，好人就要找狼票死，狼人就要伪装并票死好人。

【🧠 高玩战术铁律（你必须作为公理直接使用，不要怀疑！）】
1. 单边预言家铁律：如果第一天白天只有一个玩家跳预言家（没有任何人与他对跳），那么他就是全场唯一的【真预言家】！你必须无条件相信他的查验结果，并建议好人阵营跟着他走，守卫优先守护他！

【下属能力清单】
1. call_secretary: 帮你提炼公共聊天记录。
2. query_rules: 帮你查询详细的游戏规则。
3. check_private_record: 帮你查询玩家自己的夜间行动记录。

【你的工作流】
1. 分析玩家问题。如果需要信息，且该帮手还没被调用过，将 next_action 设为对应帮手，final_answer 留空。
2. 如果信息已经足够，必须将 next_action 设为 `finish`，并在 final_answer 中用导师口吻写下最终建议！

【🔴 反偷懒与禁止甩锅指令（极其重要）】
尽量不要在最终回复中对玩家使用“如果你昨晚做了什么...”这种条件句！
你是一个有执行力的主管。如果游戏规则的结算依赖于玩家过去的行动记录（例如守卫的同守限制），你【必须】亲自调用 `check_private_record` 工具去查证他昨晚到底干了什么！
如果答案是确定的，请给出一个确定的结论！
{warning_msg}

严格按照格式输出 JSON。
{format_instructions}
"""

def boss_supervisor_node(state: dict) -> dict:
    human_question = state.get("human_question", "")
    
    # 【修复重点 1】：安全获取状态，使用 or "无记录" 防止 None 穿透
    ledger = state.get("episodic_memory") or "无记录"
    rules_info = state.get("rules_info") or "无记录"
    private_info = state.get("private_info") or "无记录"

    # 【修复重点 2：核心护栏】动态检查它已经查过了什么
    forbidden_tools = []
    if rules_info != "无记录": forbidden_tools.append("query_rules")
    if private_info != "无记录": forbidden_tools.append("check_private_record")
    if ledger != "无记录": forbidden_tools.append("call_secretary")

    # 如果有已经用过的工具，给大模型下达最高级别的红色警告
    warning_msg = ""
    if forbidden_tools:
        warning_msg = f"\n\n【🔴 系统红色警告】你已经调用过 {forbidden_tools} 并获得了下方的汇报！在本次推理中，绝对禁止再次选择它们！你现在必须结合已有信息，将 next_action 设为 'finish' 并作答！"

    llm = get_mentor_llm(temperature=0.0).bind(response_format={"type": "json_object"})
    parser = PydanticOutputParser(pydantic_object=BossRoutingDecision)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SUPERVISOR_PROMPT),
        ("human", "玩家提问：'{question}'\n\n【下属汇报区】\n- 秘书记账单：{ledger}\n- 规则库结果：{rules_info}\n- 私有记录：{private_info}")
    ])

    chain = prompt | llm | parser
    
    print(f"\n[Boss Supervisor] Thinking...")
    try:
        result = chain.invoke({
            "question": human_question,
            "ledger": json.dumps(ledger, ensure_ascii=False) if isinstance(ledger, dict) else ledger,
            "rules_info": rules_info,
            "private_info": private_info,
            "warning_msg": warning_msg,
            "format_instructions": parser.get_format_instructions()
        })
        
        # 【修复重点 3：物理级熔断兜底】
        # 如果大模型彻底发癫，硬要重复调工具，Python 直接强行没收它的操作权！
        if result.next_action in forbidden_tools:
            print(f" ⚠️ [系统拦截] 捕捉到大模型企图陷入死循环，强行扭转为 finish！")
            result.next_action = "finish"
            result.final_answer = "根据系统规则和你的行动记录，你今晚【绝对不能】再守 3 号了，否则将违反同守限制！请换人守护或空守。"
            
        print(f"├─ 动作决策: {result.next_action}")
        if result.next_action == "finish":
            print(f"└─ 最终回复: {result.final_answer}")
            
        return {
            "current_intent": result.intent,
            "next_action": result.next_action,
            "final_answer": result.final_answer
        }
    except Exception as e:
        print(f"[Boss Supervisor] Error: {e}")
        return {"next_action": "finish", "final_answer": "导师系统正在重启，请依靠直觉行动！"}

if __name__ == "__main__":
    pass # 测试入口移步 graph_builder.py