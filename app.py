import streamlit as st
import os
from dotenv import load_dotenv
from llm_client import LLMClient
from game import Game, create_players

# 网页全局配置
st.set_page_config(page_title="LLM 狼人杀沙盒", page_icon="🐺", layout="wide")
st.title("🐺 LLM 狼人杀多智能体沙盒 | 观战模式")

# ==========================================
# 🧠 状态保持 (Session State)
# ==========================================
if "game_engine" not in st.session_state:
    st.session_state.game_engine = None
    st.session_state.current_phase = "Night"
    st.session_state.dead_tonight = []
    
    # 新增的排队机与状态标记
    st.session_state.day_initialized = False # 标记今天是否已经宣布过死讯
    st.session_state.day_sub_phase = "discuss" # 白天分为：discuss(发言) -> vote(投票)
    st.session_state.speaker_queue = [] # 发言排队机
    st.session_state.voter_queue = []   # 投票排队机
    st.session_state.votes_dict = {}    # 投票箱 {目标座位号: 票数}

    st.session_state.night_initialized = False 
    st.session_state.night_sub_phase = "wolf_discuss" # 黑夜子阶段
    st.session_state.wolf_chat_history = []           # 狼人专属的加密聊天记录
    st.session_state.wolf_speaker_queue = []          # 狼人发言排队机
    st.session_state.wolf_voter_queue = []            # 狼人刀人排队机

# ==========================================
# 🎛️ 左侧：控制台与状态面板
# ==========================================
with st.sidebar:
    st.header("⚙️ 游戏控制台")
    
    # 启动按钮
    if st.button("初始化新对局 (7 AI)", use_container_width=True):
        with st.spinner("正在连接模型 API，生成并分配 Agent..."):
            load_dotenv()
            client = LLMClient(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL"))
            brain_map = {i: client for i in range(1, 8)}
            
            players_list = create_players(brain_map, human_seat=7)
            # 把你的座位号存进 session_state，方便全局调用
            st.session_state.human_seat = 7
            game = Game(players_list, delay_sec=0) 
            game._setup_wolves() 
            
            st.session_state.game_engine = game
            st.session_state.current_phase = "Night"
            st.rerun()

    # 场上状态雷达图
    if st.session_state.game_engine:
        st.divider()
        st.subheader("📋 场上玩家状态")
        for seat, player in st.session_state.game_engine.players.items():
            status_icon = "🟢" if player.is_alive else "💀"
            status_text = "存活" if player.is_alive else "出局"
            
            if seat == st.session_state.get("human_seat"):
                role_display = f"🎴 {player.role} (你)"
            else:
                role_display = "❓ 未知身份"
                
            st.markdown(f"**{seat}号** | {status_icon} {status_text} | {role_display}")
# ==========================================
# 📺 右侧：主游戏对讲机与推演区
# ==========================================
if st.session_state.game_engine:
    game = st.session_state.game_engine
    
    # 1. 渲染聊天历史
    for msg in game.public_chat_history:
        role = msg["role"]
        content = msg["content"]
        avatar = "⚖️" if role == "system" else "🤖"
        st.chat_message(role, avatar=avatar).write(content)

    # 2. 状态机推进逻辑
    if not game.game_over():
        st.divider()
        if st.session_state.current_phase == "Night":
            human_player = game.players.get(st.session_state.get("human_seat"))
            # 身份权限校验卡
            is_human_wolf = human_player and human_player.faction.name == "WOLF"
            is_human_guard = human_player and human_player.role == "Guard"
            is_human_seer = human_player and human_player.role == "Seer"

            # 1. 黑夜初始化
            if not st.session_state.night_initialized:
                alive_wolves = [p for p in game.players.values() if p.faction.name == "WOLF" and p.is_alive]
                st.session_state.wolf_speaker_queue = alive_wolves.copy()
                st.session_state.wolf_chat_history = []
                
                # 定义黑夜行动队列：战术讨论 -> 狼人刀人 -> 守卫行动 -> 预言家验人 -> 结算天亮
                st.session_state.night_queue = ["wolf_discuss", "wolf_kill", "guard_action", "seer_action", "settle"]
                st.session_state.night_results = {"guard_target": None, "wolf_kill": None}
                st.session_state.night_initialized = True
                st.rerun()

            st.error("🌙 [机密] 当前为黑夜阶段")
            
            # 排队机开始运转
            if st.session_state.night_queue:
                current_action = st.session_state.night_queue[0]

                # ------------------------------------------------
                # 🐺 1. 狼人战术商讨 (你再也看不到了！)
                # ------------------------------------------------
                if current_action == "wolf_discuss":
                    if is_human_wolf:
                        st.subheader("🐺 狼人加密通讯频道")
                        for msg in st.session_state.wolf_chat_history:
                            st.chat_message("user", avatar="🐺").write(msg["content"])
                    else:
                        st.info("🌙 夜黑风高，狼人们正在后台密谋...")

                    if st.session_state.wolf_speaker_queue:
                        current_wolf = st.session_state.wolf_speaker_queue[0]
                        if current_wolf.is_human:
                            wolf_input = st.chat_input("🐺 嘘！输入你的暗杀计划...")
                            if wolf_input:
                                st.session_state.wolf_chat_history.append({"role": "user", "content": f"{current_wolf.seat}号 (你): {wolf_input}"})
                                st.session_state.wolf_speaker_queue.pop(0)
                                st.rerun()
                            else:
                                st.stop()
                        else:
                            # 掩护提示词：好人只看到模糊的转圈圈，狼人能看到具体谁在思考
                            spinner_msg = f"🐺 队友 {current_wolf.seat} 号正在思考..." if is_human_wolf else "🌙 狼人行动中..."
                            with st.spinner(spinner_msg):
                                game_info = {"alive_players": [p for p in game.players.values() if p.is_alive]}
                                speech = current_wolf.night_discuss(st.session_state.wolf_chat_history, game_info)
                                st.session_state.wolf_chat_history.append({"role": "user", "content": f"{current_wolf.seat}号: {speech}"})
                                st.session_state.wolf_speaker_queue.pop(0)
                                st.rerun()
                    else:
                        if is_human_wolf:
                            st.success("✅ 战术商讨完毕。")
                            if st.button("🔪 结束讨论，进入刀人阶段", type="primary"):
                                st.session_state.night_queue.pop(0)
                                st.rerun()
                        else:
                            # 非狼人玩家自动流转，绝不卡顿
                            st.session_state.night_queue.pop(0)
                            st.rerun()

                # ------------------------------------------------
                # 🔪 2. 狼人刀人 (彻底告别终端 input)
                # ------------------------------------------------
                elif current_action == "wolf_kill":
                    alive_wolves = [p for p in game.players.values() if p.faction.name == "WOLF" and p.is_alive]
                    if is_human_wolf:
                        st.subheader("🔪 狼人刀人执行")
                        kill_input = st.chat_input("请输入你要暗杀的座号 (纯数字)：")
                        if kill_input:
                            try:
                                target = int(kill_input.strip())
                                st.session_state.night_results["wolf_kill"] = target
                                st.session_state.night_queue.pop(0)
                                st.rerun()
                            except ValueError:
                                st.stop()
                        else:
                            st.info("🔪 狼队等待你的最终击杀指令...")
                            st.stop()
                    else:
                        with st.spinner("🌙 狼人正在执行暗杀..."):
                            votes = {}
                            for w in alive_wolves:
                                target = w.night_kill(st.session_state.wolf_chat_history)
                                if target: votes[target] = votes.get(target, 0) + 1
                            if votes:
                                final_target = max(votes, key=votes.get)
                                st.session_state.night_results["wolf_kill"] = final_target
                            st.session_state.night_queue.pop(0)
                            st.rerun()

                # ------------------------------------------------
                # 🛡️ 3. 守卫行动 (属于你的专属高光时刻)
                # ------------------------------------------------
                elif current_action == "guard_action":
                    guard = next((p for p in game.players.values() if p.role == "Guard" and p.is_alive), None)
                    if guard:
                        if guard.is_human:
                            st.subheader("🛡️ 守卫专属行动")
                            guard_input = st.chat_input("请输入你要守护的座号 (输入 0 空守)：")
                            if guard_input:
                                try:
                                    target = int(guard_input.strip())
                                    st.session_state.night_results["guard_target"] = target if target != 0 else None
                                    st.success(f"你选择守护了 {target} 号。")
                                    # 稍作停顿，让你看清守护结果，必须点按钮才进入下一步
                                    if st.button("🛡️ 确认并闭眼"):
                                        st.session_state.night_queue.pop(0)
                                        st.rerun()
                                    else:
                                        st.stop()
                                except ValueError:
                                    st.warning("❌ 请输入数字！")
                                    st.stop()
                            else:
                                st.info("🛡️ 今晚你要守护谁？等待你的决定...")
                                st.stop()
                        else:
                            with st.spinner("🌙 某个神职正在行动..."):
                                game_info = {"alive_players": [p for p in game.players.values() if p.is_alive]}
                                action = guard.night_action(game_info)
                                st.session_state.night_results["guard_target"] = action['target'] if action else None
                                st.session_state.night_queue.pop(0)
                                st.rerun()
                    else:
                        st.session_state.night_queue.pop(0)
                        st.rerun()

                # ------------------------------------------------
                # 🔮 4. 预言家验人
                # ------------------------------------------------
                elif current_action == "seer_action":
                    seer = next((p for p in game.players.values() if p.role == "Seer" and p.is_alive), None)
                    if seer:
                        if seer.is_human:
                            st.subheader("🔮 预言家专属行动")
                            seer_input = st.chat_input("请输入你要查验的座号：")
                            if seer_input:
                                try:
                                    target = int(seer_input.strip())
                                    target_player = game.players.get(target)
                                    if target_player:
                                        is_wolf = target_player.faction.name == "WOLF"
                                        seer.update_verification(target, is_wolf)
                                        result_text = "狼人" if is_wolf else "好人"
                                        st.success(f"查验完毕！{target} 号玩家是：【{result_text}】")
                                        if st.button("🔮 知道了，闭眼"):
                                            st.session_state.night_queue.pop(0)
                                            st.rerun()
                                        else:
                                            st.stop()
                                    else:
                                        st.warning("玩家不存在")
                                        st.stop()
                                except ValueError:
                                    st.stop()
                            else:
                                st.info("🔮 等待你选择查验目标...")
                                st.stop()
                        else:
                            with st.spinner("🌙 某个神职正在行动..."):
                                game_info = {"alive_players": [p for p in game.players.values() if p.is_alive]}
                                action = seer.night_action(game_info)
                                if action and action["target"]:
                                    t_seat = action["target"]
                                    t_player = game.players.get(t_seat)
                                    if t_player:
                                        seer.update_verification(t_seat, t_player.faction.name == "WOLF")
                                st.session_state.night_queue.pop(0)
                                st.rerun()
                    else:
                        st.session_state.night_queue.pop(0)
                        st.rerun()

                # ------------------------------------------------
                # ⚖️ 5. 夜晚结算，安全切回白天
                # ------------------------------------------------
                elif current_action == "settle":
                    with st.spinner("黎明即将到来，结算昨晚伤亡..."):
                        dead_tonight = []
                        kill_target = st.session_state.night_results["wolf_kill"]
                        guard_target = st.session_state.night_results["guard_target"]
                        
                        # 结算逻辑：刀中且没被守卫守住，则死亡
                        if kill_target and kill_target != 0:
                            if kill_target != guard_target:
                                dead_tonight.append(kill_target)
                                game.players[kill_target].is_alive = False
                                
                        # 将结果传给白天，切回白天状态机！
                        st.session_state.dead_tonight = dead_tonight
                        st.session_state.night_initialized = False
                        st.session_state.day_initialized = False
                        st.session_state.current_phase = "Day"
                    st.rerun()
                
        elif st.session_state.current_phase == "Day":
            
            # 1. 黎明初始化：宣布死讯，并把活人塞进排队机
            if not st.session_state.day_initialized:
                alive_players = game.web_announce_day(st.session_state.dead_tonight)
                # 复制两份名单，一份用来发言，一份用来投票
                st.session_state.speaker_queue = alive_players.copy()
                st.session_state.voter_queue = alive_players.copy()
                st.session_state.votes_dict = {}
                st.session_state.day_sub_phase = "discuss"
                st.session_state.day_initialized = True
                st.rerun()

            # ------------------------------------------------
            # 💬 白天子阶段 A：依次发言
            # ------------------------------------------------
            if st.session_state.day_sub_phase == "discuss":
                if st.session_state.speaker_queue:
                    current_player = st.session_state.speaker_queue[0]
                    
                    if current_player.is_human:
                        human_input = st.chat_input(f"🔔 你的回合！请输入你（{current_player.seat}号）的发言...")
                        if human_input:
                            game.public_chat_history.append({"role": "user", "content": f"🧑 {current_player.seat} 号 (你) 说: {human_input}"})
                            st.session_state.speaker_queue.pop(0)
                            st.rerun()
                        else:
                            st.info(f"👉 正在等待 {current_player.seat} 号 (你) 发言...")
                            st.stop() # 卡住网页，等待人类输入
                    else:
                        with st.spinner(f"🤖 {current_player.seat} 号正在疯狂组织语言..."):
                            speech = current_player.speak(game.public_chat_history, None)
                            game.public_chat_history.append({"role": "user", "content": f"🤖 {current_player.seat} 号玩家说: {speech}"})
                            st.session_state.speaker_queue.pop(0)
                            st.rerun()
                else:
                    # 发言队列空了，自动进入投票环节！
                    game.public_chat_history.append({"role": "system", "content": f"⚖️ 所有存活玩家发言完毕，现在进入投票环节。"})
                    st.session_state.day_sub_phase = "vote"
                    st.rerun()

            # ------------------------------------------------
            # 🗳️ 白天子阶段 B：依次投票
            # ------------------------------------------------
            elif st.session_state.day_sub_phase == "vote":
                if st.session_state.voter_queue:
                    current_voter = st.session_state.voter_queue[0]
                    
                    if current_voter.is_human:
                        # 召唤底部输入框让玩家投票（只能输入数字）
                        vote_input = st.chat_input(f"🔔 轮到你投票了！请输入你要放逐的玩家座号 (输入 0 弃票)...")
                        if vote_input:
                            try:
                                target = int(vote_input.strip())
                                alive_seats = [p.seat for p in game.players.values() if p.is_alive]
                                
                                if target != 0 and target not in alive_seats:
                                    st.warning(f"❌ {target} 号玩家不存在或已死亡，请重新输入活着的玩家座号！")
                                    st.stop()
                                
                                # 记票
                                if target != 0:
                                    st.session_state.votes_dict[target] = st.session_state.votes_dict.get(target, 0) + 1
                                    game.public_chat_history.append({"role": "user", "content": f"🧑 {current_voter.seat} 号 (你) 投票放逐了 {target} 号"})
                                else:
                                    game.public_chat_history.append({"role": "user", "content": f"🧑 {current_voter.seat} 号 (你) 选择了弃票"})
                                
                                st.session_state.voter_queue.pop(0)
                                st.rerun()
                            except ValueError:
                                st.warning("❌ 格式错误，请输入纯数字！")
                                st.stop()
                        else:
                            st.info(f"👉 正在等待 {current_voter.seat} 号 (你) 做出投票决定...")
                            st.stop()
                    else:
                        with st.spinner(f"🤖 {current_voter.seat} 号正在抉择把票投给谁..."):
                            alive_seats = [p.seat for p in game.players.values() if p.is_alive]
                            target = current_voter.vote(game.public_chat_history, game_info={"alive_players": alive_seats})
                            
                            if target and target != 0 and target in alive_seats:
                                st.session_state.votes_dict[target] = st.session_state.votes_dict.get(target, 0) + 1
                                game.public_chat_history.append({"role": "user", "content": f"🤖 {current_voter.seat} 号投票放逐了 {target} 号"})
                            else:
                                game.public_chat_history.append({"role": "user", "content": f"🤖 {current_voter.seat} 号选择了弃票"})
                            
                            st.session_state.voter_queue.pop(0)
                            st.rerun()
                else:
                    # 投票队列空了，开始结算！
                    with st.spinner("⚖️ 正在结算投票结果..."):
                        game.web_resolve_voting(st.session_state.votes_dict)
                        game.day_count += 1
                        
                        # 重置白天的标记，把状态机切回夜晚！
                        st.session_state.day_initialized = False
                        st.session_state.current_phase = "Night"
                        st.rerun()
    else:
        st.success(f"对局结束。获胜阵营：【{game.winner.value}】")
else:
    st.info("👈 请点击左侧【初始化新对局】按钮生成游戏环境。")