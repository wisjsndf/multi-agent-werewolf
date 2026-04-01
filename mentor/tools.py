import os

# ==========================================
# 工具节点 1：规则查询器 (Markdown 满血版)
# ==========================================
def rules_tool_node(state: dict) -> dict:
    print(" 🛠️ [Tool] 正在翻阅全局《游戏规则手册.md》...")
    
    # 动态获取项目根目录下的 game_rules.md
    rule_path = os.path.join(os.path.dirname(__file__), '..', 'game_rules.md')
    
    try:
        with open(rule_path, 'r', encoding='utf-8') as f:
            # 现在的 DeepSeek 极其聪明且便宜，直接把整本手册拍给它看！
            # 彻底杜绝 RAG 带来的“断章取义”和死循环问题
            rules_info = f"【系统完整规则手册】\n{f.read()}"
    except Exception as e:
        print(f" ⚠️ [Warning] 规则文件读取失败: {e}")
        rules_info = "规则文件读取失败，请遵循标准狼人杀逻辑。"
    
    return {"rules_info": rules_info}


# ==========================================
# 工具节点 2：私有状态查询器 (权限隔离版)
# ==========================================
def private_tool_node(state: dict) -> dict:
    print(" 🛠️ [Tool] 正在检索玩家的私有夜间行动记录...")
    
    # 这个 record 是 game_engine 强行注入的绝对真理，大模型无法篡改
    record = state.get("my_night_record", "")
    
    if not record:
        return {"private_info": "系统记录：你昨晚没有任何行动记录。"}
        
    return {"private_info": f"系统记录：{record}"}