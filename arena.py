from llm_client import LLMClient
from game import Game, create_players
import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
import sys

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

        players_list = create_players(brain_map)
        game = Game(players_list, delay_seconds=0)
        
        original_stdout = sys.stdout

        if not verbose:
            sys.stdout = open(os.devnull, 'w')

        try:
            winner = game.start_game()
        finally:
            if not verbose:
                sys.stdout.close()
                sys.stdout = original_stdout
        
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