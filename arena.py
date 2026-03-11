from llm_client import LLMClient
from game import Game, create_players
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
import sys
import json
from baseline_tutor import run_baseline_prediction

def run_arena(num_games, verbose):
    load_dotenv()
    
    client_deepseek = LLMClient(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
        model_name="deepseek-chat"
    )

    client_doubao = LLMClient(
        api_key=os.getenv("DOUBAO_API_KEY"),
        base_url=os.getenv("DOUBAO_BASE_URL"),
        model_name="doubao-seed-2-0-lite-260215"
    )

    client_hunyuan = LLMClient(
        api_key=os.getenv("HUNYUAN_API_KEY"),
        base_url=os.getenv("HUNYUAN_BASE_URL"),
        model_name="hunyuan-turbo"
    )

    client_qwen = LLMClient(
        api_key=os.getenv("QWEN_API_KEY"),
        base_url=os.getenv("QWEN_BASE_URL"),
        model_name="qwen-plus"
    )

    brain_map = {
        1: client_qwen,
        2: client_qwen,
        3: client_hunyuan,
        4: client_doubao,
        5: client_doubao,
        6: client_deepseek,
        7: client_deepseek,        
    }

    wolf_wins = 0
    villager_wins = 0
    game_results = []
    seat_stats = {seat: {"wins": 0, "games": 0} for seat in range(1, 8)}
    baseline_eval_results = []

    eval_metrics = {
        1: {"recalls": [], "margins": []},
        2: {"recalls": [], "margins": []}
    }

    print(f"评测模式启动！将连续进行 {num_games} 场游戏...\n")

    if not verbose:
        print("（提示：当前为简洁模式，游戏过程中的详细信息将被隐藏。开启 verbose 模式可查看完整日志。）\n")
    
    for i in range(num_games):
        if not verbose:
            print(f"===正在进行第 {i+1} / {num_games} 局===", end="\r")
        else:
            print(f"\n=============================")
            print(f"正在进行第 {i+1} / {num_games} 局")
            print(f"=============================\n")

        current_game_predictions = {}

        def evaluation_hook(current_game):
            if current_game.day_count in [1, 2]:
                if verbose:
                    print(f"\n  [评测探头] 正在收集第 {current_game.day_count} 天的基线预测数据...")

                alive_seats = [p.seat for p in current_game.players.values() if p.is_alive]

                preds = run_baseline_prediction(
                    client_deepseek,
                    current_game.public_chat_history,
                    alive_seats
                )

                current_game_predictions[current_game.day_count] = preds
                
        players_list = create_players(brain_map)
        game = Game(players_list, delay_seconds=0, before_vote_callback=evaluation_hook)
        
        original_stdout = sys.stdout

        if not verbose:
            sys.stdout = open(os.devnull, 'w')

        try:
            winner = game.start_game()
        finally:
            if not verbose:
                sys.stdout.close()
                sys.stdout = original_stdout
        
        ground_truth = {str(p.seat): p.role for p in game.players.values()}

        game_record = {
            "game_id": i + 1,
            "winner": winner.name if winner else "UNKNOWN",
            "ground_truth": ground_truth,
            "public_chat": game.public_chat_history,      # 给高级导师看的阳光数据
            "secret_wolf_chat": game.wolf_chat_history    # 封印的狼人密谋，绝对不能给导师看
        }
        with open("rag_database.jsonl", "a", encoding="utf-8") as db_file:
            db_file.write(json.dumps(game_record, ensure_ascii=False) + "\n")

        baseline_eval_results.append({
            "game_id": i + 1,
            "ground_truth": ground_truth,
            "predictions": current_game_predictions
        })

        for day, preds in current_game_predictions.items():
            if not preds: 
                continue # 万一导师没输出东西，直接跳过
            
            alive_seats = [str(k) for k in preds.keys()]
            
            # 找出活着的真狼和真好人
            actual_wolves = [s for s in alive_seats if "WOLF" in ground_truth.get(s, "").upper()]
            actual_goods = [s for s in alive_seats if s not in actual_wolves]
            
            # (1) 算 Top-2 召回率
            sorted_seats = sorted(alive_seats, key=lambda k: float(preds[k]), reverse=True)
            top_2_seats = sorted_seats[:2] # 导师觉得最像狼的两个人
            
            hits = sum(1 for seat in top_2_seats if seat in actual_wolves)
            recall = (hits / len(actual_wolves)) if actual_wolves else 0.0
            eval_metrics[day]["recalls"].append(recall) # 存入大盘
            
            # (2) 算 置信度差值 (Margin)
            p_wolves = [float(preds[s]) for s in actual_wolves]
            p_goods = [float(preds[s]) for s in actual_goods]
            
            avg_p_wolf = (sum(p_wolves) / len(p_wolves)) if p_wolves else 0.0
            avg_p_good = (sum(p_goods) / len(p_goods)) if p_goods else 0.0
            
            margin = avg_p_wolf - avg_p_good
            eval_metrics[day]["margins"].append(margin)


        if winner and winner.name == "WOLF":
            wolf_wins += 1
            game_results.append(f"第 {i+1} 局：狼人胜利")
        elif winner and winner.name == "VILLAGER":
            villager_wins += 1
            game_results.append(f"第 {i+1} 局：好人胜利")
        else:
            game_results.append(f"第 {i+1} 局：未知结果")

        if winner:
            for player in game.players.values():
                seat_stats[player.seat]["games"] += 1
                
                is_wolf_win = (winner.name == "WOLF" and player.faction.name == "WOLF")
                is_good_win = (winner.name == "VILLAGER" and player.faction.name in ["VILLAGER", "GOD"])
                
                if is_wolf_win or is_good_win:
                    seat_stats[player.seat]["wins"] += 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"evaluation_report_{timestamp}.txt"

    wolf_win_rate = (wolf_wins / num_games) * 100 if num_games > 0 else 0
    villager_win_rate = (villager_wins / num_games) * 100 if num_games > 0 else 0

    report_content = (
        f"狼人杀AI智能体评测报告\n"
        f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"总游戏局数：{num_games}\n"
        f"====================================================\n"
        f"环境平衡性评测结果：\n"
        f"狼人胜率：{wolf_win_rate:.2f}% ({wolf_wins} 胜)\n"
        f"好人胜率：{villager_win_rate:.2f}% ({villager_wins} 胜)\n"
        f"====================================================\n"
        f"每个座位的胜率统计：\n"
    )

    for seat in range(1, 8):
        games_played = seat_stats[seat]["games"]
        wins = seat_stats[seat]["wins"]
        win_rate = (wins / games_played) * 100 if games_played > 0 else 0
        report_content += f"座位 {seat} 胜率: {win_rate:.2f}% ({wins}/{games_played})\n"

    report_content += f"\n========================================\n📝 单局结果明细：\n"
    for res in game_results:
        report_content += res + "\n"

    report_content += f"\n====================================================\n"
    report_content += f"基线导师 (DeepSeek-Chat) 核心量化指标：\n"
    report_content += f"====================================================\n"
    
    for day in [1, 2]:
        recalls = eval_metrics[day]["recalls"]
        margins = eval_metrics[day]["margins"]
        
        if recalls and margins:
            avg_recall = sum(recalls) / len(recalls)
            avg_margin = sum(margins) / len(margins)
            
            report_content += f"【Day {day} 表现】(有效评估: {len(recalls)} 局)\n"
            report_content += f"  Top-2 狼人召回率: {avg_recall * 100:.2f}%\n"
            report_content += f"  置信度差值(Margin): {avg_margin:.4f} (范围 -1 到 1，越高越准)\n\n"
        else:
            report_content += f"【Day {day} 表现】数据不足，无有效评估。\n\n"

    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report_content)

    print("\n\n === 测试结束 ===")
    print(f"狼人胜率: {wolf_win_rate:.2f}% | 好人胜率: {villager_win_rate:.2f}%")
    print("各座位胜率已写入报告！")
    print(f"详细评测报告已生成：{report_filename}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="狼人杀多智能体评测系统 (Arena Mode)")
    parser.add_argument("-n", "--num", type=int, default=5, help="要测试的游戏局数 (例如: python arena.py -n 10)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细的游戏对话过程（默认后台静默全速运行）")
    args = parser.parse_args()
    
    run_arena(args.num, args.verbose)