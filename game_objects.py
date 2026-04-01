import re
from enum import Enum
import prompts
from mentor_hook import get_human_input_with_mentor

class Faction(Enum):
    WOLF = 1
    VILLAGER = 2
    GOD = 3


class Player:
    def __init__(self, seat, role, faction, llm_client, is_human=False):
        self.seat = seat
        self.role = role
        self.faction = faction
        self.llm_client = llm_client
        self.is_alive = True
        self.is_human = is_human

    def night_action(self, game_info):
        return None
    
    def get_private_state(self):
        """
        供mentor调用，获取该角色的私有记忆/状态
        """
        return "平民没有任何夜晚行动记录和私有视角。"

    def ask_ai_to_speak(self, history, instruction):

        if self.is_human:
            prompt_text = f"\n 🔔 [你的回合] 系统提示：{instruction}\n 请输入你 ({self.seat}号 {self.role}) 的发言"
            
            user_input = get_human_input_with_mentor(
                game_instance=self.game,
                human_player=self,
                stage_name="DAY_SPEECH", 
                prompt_text=prompt_text
            )
            return user_input

        system_content = prompts.SYSTEM_CONTENT_BASE.format(
            role=self.role,
            seat=self.seat,
            team=self.faction.name
        )

        messages = [
            {"role": "system", "content": system_content},
            *history,
            {"role": "user", "content": instruction}
        ]
        try:
            #print(f"  ... 这位玩家正在思考 ...")
            response = self.llm_client.send_prompt(messages)
            return response
        except Exception as e:
            print(f"Error while asking AI to speak: {e}")
            return "过。"
        
    def ask_ai_for_number(self, history, instruction):

        if self.is_human:
            prompt_text = f"\n 🔔 [你的回合] 系统提示：{instruction}\n👉 请输入目标座位号 (输入 0 代表弃权/空过)"
            while True:
                user_input = get_human_input_with_mentor(
                    game_instance=self.game,
                    human_player=self,
                    stage_name="ACTION_PHASE",
                    prompt_text=prompt_text
                )
                try:
                    target = int(user_input.strip())
                    return target if target != 0 else None
                except ValueError:
                    print("❌ 格式错误，请输入纯数字！(或使用 /mentor 呼叫导师)")

        # 将具体的操作指令（例如刀人、守卫）和严格的数字格式要求拼接起来
        combined_instruction = f"{instruction}\n\n{prompts.ASK_FOR_NUMBER_STRICT}"
        
        raw_response = self.ask_ai_to_speak(history, combined_instruction)

        match = re.search(r'\d+', raw_response)

        if match:
            target = int(match.group())
            if target == 0:
                return None
            return target
        else:
            print(f"Warning: No valid number found in AI response: '{raw_response}'. Defaulting to None.")
            return None
        
    def speak(self, public_history, prompt_template):
        if not self.is_alive:
            return "..."
        
        return self.ask_ai_to_speak(public_history, prompt_template)
    
    def leave_last_words_killed(self, public_history):
        template = prompts.LAST_WORDS_PROMPT_KILLED.format(role=self.role)
        return self.ask_ai_to_speak(public_history, template)
    
    def leave_last_words_voted(self, public_history):
        template = prompts.LAST_WORDS_PROMPT_VOTED.format(role=self.role)
        return self.ask_ai_to_speak(public_history, template)
        
    
    def vote(self, public_history, game_info):
        if not self.is_alive:
            return None
        
        candidates = game_info['alive_players']

        vote_instruction = prompts.VOTE_INSTRUCTION.format(alive_players=candidates)

        return self.ask_ai_for_number(public_history, vote_instruction)


class Werewolf(Player):
    def __init__(self, seat, llm_client):
        super().__init__(seat, role="Werewolf", faction=Faction.WOLF, llm_client=llm_client)
        self.teammate_seats = []
    
    def set_teammates(self, teammate_seats):
        """
        游戏开始时，上帝调用此方法，告知狼人玩家同伴的座位号
        """
        self.teammate_seats = teammate_seats
    
    def night_discuss(self, private_chat_history, game_info):
        """
        阶段一：战术交流。
        输入：private_chat_history (包含之前队友说的话)
        输出：str (本人的发言)
        """
        
        # 1. 构建狼人视角的提示词
        # 关键点：必须不断提醒它谁是队友，否则它会脸盲
        candidates = []
        for p in game_info['alive_players']:
            if p.is_alive:
                candidates.append(p.seat)
        night_instruction = prompts.WEREWOLF_NIGHT_DISCUSS.format(teammate_seats=self.teammate_seats, candidates=candidates)

        # 2. 调用父类的通用发言接口
        # 父类会自动拼装 System Prompt + History + User Instruction
        return self.ask_ai_to_speak(private_chat_history, night_instruction)
    
    def night_kill(self, private_chat_history):
        """
        阶段二：确定刀人目标。
        输入：private_chat_history (包含刚才大家讨论的结果)
        输出：int (目标座位号)
        """
        
        # 1. 构建击杀提示词
        kill_instruction = prompts.WEREWOLF_NIGHT_KILL

        # 2. 调用父类的通用数字接口 (会自动进行正则解析)
        target = self.ask_ai_for_number(private_chat_history, kill_instruction)
        return target
        
    def speak(self, public_chat_history, prompt_template=None, game_info=None):
        """
        重写父类的 speak 方法。
        狼人白天必须伪装，所以我们要忽略传入的 template，强制使用狼人专属的伪装 Prompt。
        截取昨晚的讨论记录，作为加密记忆注入
        """
        
        base_instruction = prompts.WEREWOLF_DAY_DISGUISE
        tactics_instruction = ""

        if game_info and "wolf_chat_history" in game_info:
            wolf_history_list = game_info["wolf_chat_history"]

            last_night_msgs = []
            for msg in reversed(wolf_history_list):
                if msg["role"] == "system" and "天夜晚" in msg["content"]:
                    break
                if msg["role"] == "user":
                    last_night_msgs.insert(0, msg["content"])
            
            if last_night_msgs:
                memory_str = "\n".join(last_night_msgs)
                tactics_instruction = prompts.WEREWOLF_TACTICS_INJECTION.format(memory_str=memory_str)

        final_disguise_instruction = base_instruction + tactics_instruction

        return self.ask_ai_to_speak(public_chat_history, final_disguise_instruction)
    
    def vote(self, public_history, game_info):
        """
        狼人的投票逻辑：
        1. 保护队友 (除非队友已经没救了，为了倒钩可以卖)。
        2. 煽动情绪，把票投给被怀疑的好人。
        """
        if not self.is_alive:
            return None

        # 1. 构建狼人专属投票指令
        # 关键点：明确告诉它队友是谁，并且给它一个“坏人”的目标
        wolf_vote_instruction = prompts.WEREWOLF_VOTE.format(teammate_seats=self.teammate_seats, alive_players=game_info['alive_players'])
        
        # 2. 调用父类的通用接口
        # 这里实际上是在用“坏心思”去调用通用的数字决策接口
        return self.ask_ai_for_number(public_history, wolf_vote_instruction)

    def night_action(self, game_info):
        return None
    
    def get_private_state(self):
        teammates = "、".join(map(str, self.teammate_seats)) if self.teammate_seats else "无"
        return f"你的加密视角：已知狼人队友的座位号是 {teammates}。"


class Villager(Player):
    def __init__(self, seat, llm_client):
        super().__init__(seat, role="Villager", faction=Faction.VILLAGER, llm_client=llm_client)

    def speak(self, public_chat_history, prompt_template=None):
        """
        平民的发言逻辑：
        核心是【诚实】和【分析】。
        """
        
        # 这里的 Prompt 非常关键，防止 AI 平民产生幻觉（比如以为自己是预言家）
        villager_instruction = prompts.VILLAGER_DAY_SPEAK

        # 调用父类通用接口
        return self.ask_ai_to_speak(public_chat_history, villager_instruction)

class Seer(Player):
    def __init__(self, seat, llm_client):
        super().__init__(seat, role="Seer", faction=Faction.GOD, llm_client=llm_client)
        self.verified_log = {}

    def night_action(self, game_info):
        """
        预言家夜晚行动：查验身份。
        """
        if not self.is_alive:
            return None

        # 1. 获取还活着的、且没查过的玩家
        # (Game 类会传进来 alive_players 列表)
        # 这里做一个简单的过滤，AI 不需要知道谁死了，只要知道谁没查过就行
        # 但为了节省 token，最好只给它列出活人
        candidates = []
        for p in game_info['alive_players']:
            if p.seat != self.seat and p.seat not in self.verified_log:
                candidates.append(p.seat)

        # 2. 构建验人指令
        night_instruction = prompts.SEER_NIGHT_ACTION.format(verified_log=self.verified_log, candidates=candidates)

        # 3. 调用父类通用接口
        recent_history = game_info.get("recent_history", [])
        target = self.ask_ai_for_number(recent_history, night_instruction)
        
        # 返回给上帝，上帝会去判断这个人是狼是好人，然后告诉预言家结果
        return {"action": "verify", "target": target}
    
    def update_verification(self, target_seat, is_wolf):
        """
        接收查验结果并更新verified_log
        """
        identity = "狼人" if is_wolf else "好人"
        self.verified_log[target_seat] = identity
        print("  [系统提示] 预言家查验完毕")
    
    def speak(self, public_chat_history, prompt_template=None):
        """
        预言家的发言逻辑：
        核心是【起跳】和【报验人】。
        """
        
        seer_instruction = prompts.SEER_DAY_SPEAK.format(verified_log=self.verified_log)
        # 调用父类接口
        return self.ask_ai_to_speak(public_chat_history, seer_instruction)
    
    def get_private_state(self):
        if not self.verified_log:
            return "你的查验记录：空（暂未查验任何人）。"
        
        log_str = "、".join([f"第{i+1}次查 {seat}号是{identity}" for i, (seat, identity) in enumerate(self.verified_log.items())])
        return f"你的完整查验记录：{log_str}"

class Guard(Player):
    def __init__(self, seat, llm_client):
        super().__init__(seat, role="Guard", faction=Faction.GOD, llm_client=llm_client)
        self.last_guarded_seat = None

    def night_action(self, game_info):
        if not self.is_alive:
            return None
        
        valid_targets = []
        for p in game_info['alive_players']:
            if p.seat != self.last_guarded_seat:
                valid_targets.append(p.seat)
        
        guard_instruction = prompts.GUARD_NIGHT_ACTION.format(last_guarded_seat=self.last_guarded_seat, seat=self.seat, valid_targets=valid_targets)
        recent_history = game_info.get("recent_history", [])
        target = self.ask_ai_for_number(recent_history, guard_instruction)

        if target is not None and target != 0 and target not in valid_targets:
            print(f"  [系统拦截] {self.seat}号守卫试图违规守护 {target} 号，已强制转为空守。")
            target = None
        elif target == 0:
            target = None

        self.last_guarded_seat = target

        return {"action": "guard", "target": target}
    
    def speak(self, public_chat_history, prompt_template=None):
        """
        守卫的发言逻辑：
        核心是【苟活】和【暗中观察】。
        """
        
        guard_instruction = prompts.GUARD_DAY_SPEAK

        # 调用父类通用接口
        return self.ask_ai_to_speak(public_chat_history, guard_instruction)
    
    def get_private_state(self):
        if self.last_guarded_seat is None:
            return "你的守护记录：昨晚没有守护任何人（空守或游戏刚开始）。"
        return f"你的守护记录：昨晚守护了 {self.last_guarded_seat} 号。"