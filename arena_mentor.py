import os
import json
import re
import argparse
from datetime import datetime
from dotenv import load_dotenv
import sys

# 导入你的游戏引擎和角色配置
from llm_client import LLMClient
from game import Game, create_players

# 导入你辛辛苦苦搭建的多智能体导师
from mentor.graph_builder import mentor_graph

def run_mentor_arena(num_games, verbose):
    load_dotenv()
    
    # 评测场为了速度和稳定性，全场使用 DeepSeek 作为基础玩家
    client_deepseek = LLMClient(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
        model_name="deepseek-chat"
    )
    brain_map = {i: client_deepseek for i in range(1, 8)}

    # 数据统计大盘
    wolf_wins = 0
    villager_wins = 0
    eval_metrics = {1: {"recalls": [], "margins": []}, 2: {"recalls": [], "margins": []}}

    print(f"\n🐺 [Mentor Arena] 导师智能体专属评测场启动！将连续进行 {num_games} 场游戏...\n")

    for i in range(num_games):
        if not verbose:
            print(f"=== 正在进行第 {i+1} / {num_games} 局 ===", end="\r")
        else:
            print(f"\n{'='*40}\n正在进行第 {i+1} / {num_games} 局\n{'='*40}\n")

        current_game_predictions = {}

        # ==========================================
        # 核心：专为 Mentor 设计的评测探头
        # ==========================================
        def mentor_evaluation_hook(current_game):
            day = current_game.day_count
            if day in [1, 2]:
                if verbose:
                    print(f"\n 🕵️‍♂️ [评测探头] 正在唤醒导师智能体，收集第 {day} 天的概率预测...")

                alive_seats = [p.seat for p in current_game.players.values() if p.is_alive]
                chat_str = "\n".join([msg["content"] for msg in current_game.public_chat_history])
                
                # 强迫 Boss 输出 JSON 的终极 Prompt
                strict_question = (
                    f"请评估当前存活玩家 {alive_seats} 是狼人的概率。\n"
                    "【🐺 极其重要的强制执行顺序】：\n"
                    "第一步：你现在脑子里没有任何今天的发言记录！你【必须】先将 next_action 设为 `call_secretary`，去让秘书提炼公共聊天记录！绝对不允许跳过这一步直接瞎猜！\n"
                    "第二步：等你拿到秘书汇报的记账单后，再结合逻辑推演，将 next_action 设为 `finish`。\n"
                    "【⚠️ 终极输出命令】：当你在 final_answer 中作答时，必须且只能输出一个纯 JSON 对象！键为座位号(字符串格式)，值为0到1之间的小数。例如：{{\"1\": 0.85, \"3\": 0.12}}。绝对不要输出任何分析过程、问候语或 Markdown 标记！"
                )
                
                safe_state = {
                    "human_question": strict_question,
                    "current_day": day,
                    "stage": "DAY_VOTE",
                    "alive_players": alive_seats,
                    "my_role": "上帝", 
                    "my_night_record": "上帝视角，无私有操作。",
                    "short_term_memory": chat_str
                }
                
                preds = {}
                try:
                    result = mentor_graph.invoke(safe_state)
                    answer_text = result.get('final_answer', '')
                    match = re.search(r'\{.*\}', answer_text, re.DOTALL)
                    if match:
                        preds_raw = json.loads(match.group())
                        preds = {str(k): float(v) for k, v in preds_raw.items() if int(k) in alive_seats}
                except Exception as e:
                    if verbose: print(f"❌ 导师解析失败: {e}")
                
                # 兜底：如果没输出合法 JSON，默认给 0.5
                if not preds:
                    preds = {str(seat): 0.5 for seat in alive_seats}
                    
                current_game_predictions[day] = preds

        # ==========================================
        # 启动单局游戏
        # ==========================================
        players_list = create_players(brain_map)
        game = Game(players_list, delay_seconds=0, before_vote_callback=mentor_evaluation_hook)
        
        original_stdout = sys.stdout
        if not verbose:
            sys.stdout = open(os.devnull, 'w')

        try:
            winner = game.start_game()
        finally:
            if not verbose:
                sys.stdout.close()
                sys.stdout = original_stdout

        # ==========================================
        # 战后结算与指标计算
        # ==========================================
        ground_truth = {str(p.seat): p.role for p in game.players.values()}
        if winner and winner.name == "WOLF": wolf_wins += 1
        elif winner and winner.name == "VILLAGER": villager_wins += 1

        for day, preds in current_game_predictions.items():
            if not preds: continue 
            
            alive_seats = [str(k) for k in preds.keys()]
            actual_wolves = [s for s in alive_seats if "WOLF" in ground_truth.get(s, "").upper()]
            actual_goods = [s for s in alive_seats if s not in actual_wolves]
            
            if not actual_wolves: continue # 没狼了就不算了

            # (1) Top-2 召回率
            sorted_seats = sorted(alive_seats, key=lambda k: float(preds[k]), reverse=True)
            top_2_seats = sorted_seats[:2] 
            hits = sum(1 for seat in top_2_seats if seat in actual_wolves)
            recall = hits / len(actual_wolves)
            eval_metrics[day]["recalls"].append(recall) 
            
            # (2) 置信度差值 (Margin)
            p_wolves = [float(preds[s]) for s in actual_wolves if s in preds]
            p_goods = [float(preds[s]) for s in actual_goods if s in preds]
            avg_p_wolf = sum(p_wolves) / len(p_wolves) if p_wolves else 0.0
            avg_p_good = sum(p_goods) / len(p_goods) if p_goods else 0.0
            margin = avg_p_wolf - avg_p_good
            eval_metrics[day]["margins"].append(margin)

    # ==========================================
    # 生成最终报告
    # ==========================================
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"mentor_arena_report_{timestamp}.txt"
    
    report_content = (
        f"🐺 多智能体导师 (Mentor Graph) 专项压测报告\n"
        f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"总对局数：{num_games}\n"
        f"{'='*50}\n"
    )

    for day in [1, 2]:
        recalls = eval_metrics[day]["recalls"]
        margins = eval_metrics[day]["margins"]
        if recalls and margins:
            avg_recall = sum(recalls) / len(recalls)
            avg_margin = sum(margins) / len(margins)
            report_content += f"【Day {day} 核心指标】(有效样本: {len(recalls)} 局)\n"
            report_content += f" 🎯 Top-2 狼人召回率: {avg_recall * 100:.2f}%\n"
            report_content += f" ⚖️ 置信度差值(Margin): {avg_margin:.4f} (越高越准)\n\n"

    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report_content)

    print("\n\n🎉 === 导师压测结束 ===")
    print(f"详细评测报告已生成：{report_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="多智能体导师专项评测系统")
    parser.add_argument("-n", "--num", type=int, default=3, help="测试局数")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细过程")
    args = parser.parse_args()
    
    run_mentor_arena(args.num, args.verbose)