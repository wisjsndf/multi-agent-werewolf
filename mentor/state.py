from typing import TypedDict, Optional, List, Union

class MentorGraphState(TypedDict):
    # ==========================================
    # 1. 引擎注入层 (绝对真理，由 game.py 传入)
    # ==========================================
    human_question: str         
    current_day: int            
    stage: str                  
    alive_players: List[int]    
    my_role: str                
    my_night_record: str        # 【新增】玩家自己的私有夜间行动记录 (权限隔离的核心)
    short_term_memory: str      
    
    # ==========================================
    # 2. 内部流转控制层 (Agent 团队内部通信)
    # ==========================================
    current_intent: Optional[str]
    next_action: Optional[str]  # 【修改】从 next_agent 改为 next_action
    
    # ==========================================
    # 3. 下属汇报区 (打工人填写的报告)
    # ==========================================
    episodic_memory: Optional[Union[dict, str]] # 秘书填的记账单
    rules_info: Optional[str]   # 【新增】规则工具查出的规则
    private_info: Optional[str] # 【新增】私有状态工具查出的记录
    semantic_memory: Optional[list] # (预留给未来的 RAG Retriever)
    
    # ==========================================
    # 4. 最终输出
    # ==========================================
    final_answer: Optional[str] # Boss 亲自写的最终回复