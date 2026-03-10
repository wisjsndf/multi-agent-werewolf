from game_objects import Faction
from game_objects import Player, Villager, Seer, Guard, Werewolf
import random
import time

def create_players(client_map, human_seat=None):
    """
    发放7人局身份牌
    :param client_map: {seat: llm_client}
    """
    # 1. 准备 7 张底牌 (2狼 1预 1守 3民)
    roles_pool = ["Werewolf", "Werewolf", "Seer", "Guard", "Villager", "Villager", "Villager"]
    
    # 2. 物理洗牌
    random.shuffle(roles_pool)
    
    players_list = []
    
    # 3. 按座位号（1 到 7）依次发牌，并生成实体对象
    print("正在洗牌发牌...")
    for index, role_name in enumerate(roles_pool):
        seat = index + 1
        client = client_map.get(seat, client_map.get(1))  # 如果没有特定座位的客户端，就用1号玩家的客户端

        is_human = (seat == human_seat)

        if role_name == "Werewolf":
            player = Werewolf(seat=seat, llm_client=client)
        elif role_name == "Seer":
            player = Seer(seat=seat, llm_client=client)
        elif role_name == "Guard":
            player = Guard(seat=seat, llm_client=client)
        else:
            player = Villager(seat=seat, llm_client=client)
            
        player.is_human = is_human
        players_list.append(player)

        if is_human:
            print(f"\n 游戏加载完毕！你是 {role_name}，座位号 {seat} 号。祝你游戏愉快！")
        print(f"  - 座位 {seat} 号：已生成玩家实体。") # 故意不打印身份，保持悬念
        
    return players_list

class Game:
    def __init__(self, players_list, delay_seconds=0, human_seat=None):
        """
        :param players_list: 玩家列表，元素是 Player 类的实例
        """
        self.players = {p.seat: p for p in players_list}
        self.public_chat_history = []
        self.wolf_chat_history = []
        self.day_count = 1
        self.winner = None
        self.delay_sec = delay_seconds
        self.human_seat = human_seat

    def print_secret(self, msg, allowed_seats):
        if self.human_seat is None or self.human_seat in allowed_seats:
            print(msg)

    def start_game(self):
        """
        游戏主循环
        """
        print("\n=== 游戏正式开始！ ===")

        self._setup_wolves()

        while not self.game_over():
            print(f"\n [第 {self.day_count} 天]")

            victim_tonight = self.night_phase()

            if self.game_over():
                break

            self.day_phase(victim_tonight)

            self.day_count += 1

        print(f"\n=== 游戏结束！获胜阵营是：{self.winner.name} ===")
        print("下面揭晓身份：")
        for player in self.players.values():
            print(f"玩家 {player.seat}: {player.role}")
    
        return self.winner
    
    def _setup_wolves(self):
        """
        初始化狼人阵营，让狼人互相知道队友的座位号。
        """
        # 获取所有狼人的座位号
        wolf_seats = [
            player.seat 
            for player in self.players.values() 
            if player.faction == Faction.WOLF
        ]
        
        # 将队友信息通知给每一只狼人
        for player in self.players.values():
            if player.faction == Faction.WOLF:
                player.set_teammates(wolf_seats)
                
        self.print_secret(f"  [加密频道] 狼人们已经互相认识了，他们的座位号是：{wolf_seats}", allowed_seats=wolf_seats)

    def night_phase(self):
        """
        夜晚阶段
        """
        print("上帝：天黑请闭眼...")

        game_info = {
            "alive_players": [p for p in self.players.values() if p.is_alive],
            "day_count": self.day_count,
            "recent_history": self.public_chat_history
        }

        wolf_seats = [p.seat for p in self.players.values() if p.faction == Faction.WOLF]
        # 1. 守卫：找到守卫，调用night_action()

        guard_target = None
        for p in self.players.values():
            if p.role == "Guard" and p.is_alive:
                action = p.night_action(game_info)
                if action:
                    guard_target = action['target']
                    self.print_secret(f"  [加密频道] {p.seat}号守卫选择守护 {guard_target} 号", allowed_seats=[p.seat])

        # 2. 狼人：_run_wolf_phase()

        wolf_kill_target = self._run_wolf_phase(game_info=game_info)

        # 3. 预言家：找到预言家，调用night_action()

        for p in self.players.values():
            if p.role == "Seer" and p.is_alive:
                action = p.night_action(game_info)
                if action and action["target"] is not None:
                    target_seat = action["target"]
                    target_player = self.players.get(target_seat)
                    if target_player:
                        is_wolf = (target_player.faction == Faction.WOLF)
                        p.update_verification(target_seat, is_wolf)
                        self.print_secret(f"  [加密频道] {p.seat}号预言家查看了 {target_seat} 号，结果是 {'狼人' if is_wolf else '好人'}", allowed_seats=[p.seat])


        # 4. 结算今晚受害者
        dead_tonight = []
        if wolf_kill_target is not None and wolf_kill_target != 0:
            if wolf_kill_target == guard_target:
                self.print_secret(f"  [加密频道] {wolf_kill_target} 号玩家被守卫成功保护了！", allowed_seats=[])
            else:
                self.print_secret(f"  [加密频道] {wolf_kill_target} 号玩家被狼人杀死了！", allowed_seats=[])
                dead_tonight.append(wolf_kill_target)
                self.players[wolf_kill_target].is_alive = False
        else:
            self.print_secret(f"  [加密频道] 今晚没有玩家被狼人杀死。", allowed_seats=[])
        return dead_tonight
    
    def _run_wolf_phase(self, game_info):
        """
        狼人商量+杀人
        """
        alive_wolves = [p for p in self.players.values() if p.faction == Faction.WOLF and p.is_alive]
        if not alive_wolves:
            return None
        
        wolf_seats = [wolf.seat for wolf in alive_wolves]
        print("  狼人们正在商量今晚的目标... ")

        # 每次讨论前，可以加一个系统提示，告诉它们今晚是第几天
        self.wolf_chat_history.append({"role": "system", "content": f"--- 第 {self.day_count} 天夜晚 ---"})

        for wolf in alive_wolves:
            # 使用 Game 类里全局的 wolf_chat_history
            speech = wolf.night_discuss(self.wolf_chat_history, game_info=game_info) 
            self.print_secret(f"    [狼人频道] {wolf.seat}号狼人说: {speech}", allowed_seats=wolf_seats)
            self.wolf_chat_history.append({"role": "user", "content": f"{wolf.seat}号说：{speech}"})

        votes = {}
        for wolf in alive_wolves:
            # 投票时也要传全局的 wolf_chat_history
            target = wolf.night_kill(self.wolf_chat_history)
            if target:
                votes[target] = votes.get(target, 0) + 1
                self.print_secret(f"    [狼人频道] {wolf.seat}号狼人投票杀死 {target} 号", allowed_seats=wolf_seats)

        if not votes:
            return None
        
        final_target = max(votes, key=votes.get)
        self.print_secret(f"  [加密频道] 狼人团队最终决定杀死 {final_target} 号玩家", allowed_seats=wolf_seats)
        return final_target

    def day_phase(self, dead_tonight):
        """
        白天阶段
        """
        print("上帝：天亮了。")
        # 1. 宣布谁死了，第一天的死者可以发言

        if not dead_tonight:
            print("  [上帝广播] 昨晚没有玩家死亡。")
            self.public_chat_history.append({"role": "system", "content": f"第 {self.day_count} 天：昨晚没有玩家死亡。"})
        else:
            dead_str = ", ".join(map(str, dead_tonight))
            print(f"  [上帝广播] 昨晚 {dead_str} 号玩家死亡了。")
            self.public_chat_history.append({"role": "system", "content": f"第 {self.day_count} 天：昨晚 {dead_str} 号玩家死亡了。"})
            if self.day_count == 1:
                for dead_seat in dead_tonight:
                    print(f"  [上帝广播] {dead_seat} 号玩家是第一天的死者，可以发言了。")
                    self.public_chat_history.append({"role": "system", "content": f"{dead_seat} 号玩家是第一天的死者，将要发表遗言。"})
                    dead_player = self.players.get(dead_seat)
                    if dead_player:
                        recent_history = self.public_chat_history
                        last_words = dead_player.leave_last_words_killed(recent_history)
                        print(f"  {dead_seat} 号玩家的遗言：{last_words}")
                        self.public_chat_history.append({"role": "user", "content": f"{dead_seat} 号玩家的遗言：{last_words}"})

                        if self.delay_sec > 0:
                            time.sleep(self.delay_sec)
        
        if self.game_over():
            return

        # 2. 活人按顺序发言，记录发言内容到 public_chat_history(?会不会后面输入的tokens特别多)

        print("  [上帝广播] 现在开始新一轮的公共发言，所有存活的玩家都可以发言了。")

        alive_players = [p for p in self.players.values() if p.is_alive]
        for player in alive_players:
            print(f"  [上帝广播] 轮到 {player.seat} 号玩家发言了。")
            recent_history = self.public_chat_history

            speech = player.speak(recent_history, prompt_template=None)
            print(f"  {player.seat} 号玩家说: {speech}")
            self.public_chat_history.append({"role": "user", "content": f"{player.seat} 号玩家说: {speech}"})

            if self.delay_sec > 0:
                time.sleep(self.delay_sec)
            
        # 3. 所有人投票 player.vote()

        print("  [上帝广播] 现在开始投票了，所有存活的玩家请投票选出你们怀疑的狼人。")
        votes = {}
        for voter in alive_players:
            recent_history = self.public_chat_history
            vote_target = voter.vote(recent_history, game_info={"alive_players": [p.seat for p in alive_players]})

            if vote_target and vote_target != 0:
                votes[vote_target] = votes.get(vote_target, 0) + 1
                print(f"    {voter.seat}号玩家投票放逐 {vote_target} 号")
            else:
                print(f"    {voter.seat}号玩家选择弃票")

            if self.delay_sec > 0:
                time.sleep(self.delay_sec * 0.5)

        # 4. 结算投票结果，放逐得票最高的玩家，被放逐的玩家发言
        
        if not votes:
            print("  [上帝广播] 没有玩家被投票放逐。")
            self.public_chat_history.append({"role": "system", "content": f"第 {self.day_count} 天：没有玩家被投票放逐。"})
            return
        
        max_votes = max(votes.values())
        candidates = [seat for seat, count in votes.items() if count == max_votes]

        if len(candidates) > 1:
            banished_seat = random.choice(candidates)
            print(f"Notice: Tie vote for players {candidates}. Player {banished_seat} is randomly selected to be banished.")
            self.public_chat_history.append({"role": "user", "content": f"今天 {candidates} 号平票，系统随机放逐了 {banished_seat} 号玩家。"})
        else:
            banished_seat = candidates[0]
            print(f"Notice: Player {banished_seat} received the most votes and is banished.")
            self.public_chat_history.append({"role": "user", "content": f"{banished_seat} 号玩家被投票放逐。"})

        banished_player = self.players.get(banished_seat)
        if banished_player:
            banished_player.is_alive = False
            print(f"  [上帝广播] {banished_seat} 号玩家被放逐了。")
            last_words = banished_player.leave_last_words_voted(self.public_chat_history)
            print(f"  {banished_seat} 号玩家的遗言：{last_words}")
            self.public_chat_history.append({"role": "user", "content": f"{banished_seat} 号玩家的遗言：{last_words}"})

            if self.delay_sec > 0:
                time.sleep(self.delay_sec)

    def web_announce_day(self, dead_tonight):
        """网页端：白天开始，只负责宣布死讯，并返回存活玩家名单"""
        if not dead_tonight:
            self.public_chat_history.append({"role": "system", "content": f"第 {self.day_count} 天：昨晚没有玩家死亡。"})
        else:
            dead_str = ", ".join(map(str, dead_tonight))
            self.public_chat_history.append({"role": "system", "content": f"第 {self.day_count} 天：昨晚 {dead_str} 号玩家死亡了。"})
            
            if self.day_count == 1:
                for dead_seat in dead_tonight:
                    dead_player = self.players.get(dead_seat)
                    if dead_player:
                        last_words = dead_player.leave_last_words_killed(self.public_chat_history)
                        self.public_chat_history.append({"role": "user", "content": f"{dead_seat} 号玩家的遗言：{last_words}"})
        
        # 返回存活玩家名单给网页队列
        return [p for p in self.players.values() if p.is_alive]
    
    def web_resolve_voting(self, votes):
        """网页端：接收网页传来的投票字典，结算谁出局"""
        if not votes:
            self.public_chat_history.append({"role": "system", "content": f"第 {self.day_count} 天：没有玩家被投票放逐。"})
            return
        
        max_votes = max(votes.values())
        candidates = [seat for seat, count in votes.items() if count == max_votes]

        if len(candidates) > 1:
            import random
            banished_seat = random.choice(candidates)
            self.public_chat_history.append({"role": "user", "content": f"今天平票，系统随机放逐了 {banished_seat} 号玩家。"})
        else:
            banished_seat = candidates[0]
            self.public_chat_history.append({"role": "user", "content": f"{banished_seat} 号玩家被投票放逐。"})

        banished_player = self.players.get(banished_seat)
        if banished_player:
            banished_player.is_alive = False
            last_words = banished_player.leave_last_words_voted(self.public_chat_history)
            self.public_chat_history.append({"role": "user", "content": f"{banished_seat} 号玩家的遗言：{last_words}"})

    def game_over(self):
        """
        检查是否屠边
        """
        alive_wolves = 0
        alive_villagers = 0
        alive_gods = 0

        for player in self.players.values():
            if player.is_alive:
                if player.faction == Faction.WOLF:
                    alive_wolves += 1
                elif player.faction == Faction.VILLAGER:
                    alive_villagers += 1
                elif player.faction == Faction.GOD:
                    alive_gods += 1

        if alive_wolves == 0:
            self.winner = Faction.VILLAGER  # 借用平民阵营代表好人胜利
            print("\n 场上所有狼人已出局，【好人阵营】获得胜利！")
            return True
            
        # 条件B：平民全灭，或者 神职全灭，狼人获胜 (屠边)
        elif alive_villagers == 0 or alive_gods == 0:
            self.winner = Faction.WOLF
            print("\n 狼人成功完成屠边，【狼人阵营】获得胜利！")
            return True

        # 5. 没人赢，游戏继续
        return False