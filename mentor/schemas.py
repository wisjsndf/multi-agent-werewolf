from pydantic import BaseModel, Field
from typing import Literal, List, Optional

# ==========================================
# Boss Agent: 意图路由 Schema
# ==========================================
class BossRoutingDecision(BaseModel):
    intent: Literal[
        "query_rules", "query_status", "query_tactics", "casual_chat", "emotional_distress"
    ] = Field(description="识别玩家意图。")
    
    reasoning: str = Field(description="你的内部思考过程。")
    
    # 【改动核心】：选项里加入了工具，且多了一个 finish！
    next_action: Literal[
        "call_secretary",        # 需要查公共聊天记录时
        "query_rules",           # 需要查游戏规则时
        "check_private_record",  # 需要查玩家昨晚的私有操作时
        "finish"                 # 信息已充足，或者只是闲聊，准备直接回复玩家
    ] = Field(description="决定下一步动作。如果下属已经汇报了所需信息，必须选择 finish！")
    
    # 【新增】：当选择 finish 时，这里就是你直接对玩家说的话
    final_answer: Optional[str] = Field(
        default=None, 
        description="当 next_action 为 'finish' 时，必须在这里写下给玩家的最终建议/回复。"
    )

# ==========================================
# 2. Secretary Agent: 情景记忆 (记账单) Schema
# ==========================================
class PlayerAction(BaseModel):
    player_id: int = Field(description="发言玩家的座位号。")
    claimed_role: Optional[str] = Field(default=None, description="玩家明示或暗示的身份。")
    target_player: Optional[int] = Field(default=None, description="被查验、保、踩的目标玩家座位号。")
    action_type: Literal["claim", "suspect", "support", "vote", "abstain"] = Field(
        description="动作类型。注意：若仅宣告自身身份，必须用 'claim' 且 target_player 留空。"
    )

class SecretaryLedger(BaseModel):
    dead_players: List[int] = Field(default_factory=list, description="本轮明确宣告死亡的玩家列表。")
    key_actions: List[PlayerAction] = Field(default_factory=list, description="提取出的场上关键行为。")
    main_conflict: Optional[str] = Field(default=None, description="当前局势核心矛盾的客观精简概括。")