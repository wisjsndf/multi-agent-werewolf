import json
from langgraph.graph import StateGraph, END
from mentor.state import MentorGraphState
from mentor.boss_node import boss_supervisor_node
from mentor.secretary_node import secretary_extraction_node
from mentor.tools import rules_tool_node, private_tool_node

# ==========================================
# 开始画图 (Cyclic Graph Construction)
# ==========================================
workflow = StateGraph(MentorGraphState)

# 1. 注册所有节点 (Nodes)
workflow.add_node("supervisor", boss_supervisor_node)
workflow.add_node("secretary", secretary_extraction_node)
workflow.add_node("rules_tool", rules_tool_node)
workflow.add_node("private_tool", private_tool_node)

# 2. 定义路由逻辑 (Conditional Edge)
def route_from_supervisor(state: dict) -> str:
    action = state.get("next_action", "finish")
    if action == "call_secretary":
        return "secretary"
    elif action == "query_rules":
        return "rules_tool"
    elif action == "check_private_record":
        return "private_tool"
    else:
        return "finish"

# 3. 连线 (Edges)
# 无论如何，档案袋永远先交给主管 Boss
workflow.set_entry_point("supervisor")

# Boss 根据路由函数的返回值，决定把档案袋丢给哪个下属，或者直接结束
workflow.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "secretary": "secretary",
        "rules_tool": "rules_tool",
        "private_tool": "private_tool",
        "finish": END  # 只有 Boss 决定 finish，整个流程才会结束！
    }
)

# 【核心架构】：所有的打工人干完活后，必须把档案袋交回给 Boss！形成循环回路。
workflow.add_edge("secretary", "supervisor")
workflow.add_edge("rules_tool", "supervisor")
workflow.add_edge("private_tool", "supervisor")

# 4. 编译成可执行的智能体系统
mentor_graph = workflow.compile()

if __name__ == "__main__":
    # ==========================================
    # 终极全链路测试！
    # ==========================================
    print("\n" + "="*50)
    print("🐺 导师智能体系统启动 (Cyclic ReAct 架构)")
    print("="*50)

    # 模拟游戏引擎 (game.py) 传过来的上帝字典
    mock_state = {
        "human_question": "今天我还能守3号吗？",
        "current_day": 2,
        "stage": "NIGHT_ACTION",
        "alive_players": [1, 2, 3, 4, 5, 6, 7],
        "my_role": "守卫",
        "my_night_record": "昨晚守护了 3 号",
        "short_term_memory": ""
    }
    
    print("\n[人类玩家] 提问:", mock_state["human_question"])
    
    # 见证奇迹的时刻
    final_state = mentor_graph.invoke(mock_state)
    
    print("\n" + "="*50)
    print("💡 【导师最终建议】:\n" + final_state["final_answer"])
    print("="*50)