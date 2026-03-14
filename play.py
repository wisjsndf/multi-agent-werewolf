# play.py
import os
import random
import time
from dotenv import load_dotenv
from llm_client import LLMClient
from game import Game, create_players

def main():
    load_dotenv()
    
    # 初始化 AI 引擎
    try:
        client_deepseek = LLMClient(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL"))
    except Exception as e:
        print(f"❌ 环境变量加载失败，请检查 .env 文件: {e}")
        return

    # 默认全场使用 DeepSeek
    brain_map = {i: client_deepseek for i in range(1, 8)}

    print("\n========================================")
    print("🐺 欢迎来到 LLM 狼人杀多智能体沙盒 🐺")
    print("========================================")
    print("请选择游戏模式：")
    print("  1. 🍿 沉浸观战模式 (7个AI神仙打架)")
    print("  2. 🎮 亲自下场模式 (人类 vs 6个AI)")
    print("========================================")

    choice = input("👉 请输入模式编号 (1 或 2): ").strip()

    human_seat = None
    delay_sec = 3  # 默认每次发言停顿 3 秒，方便人类阅读

    if choice == '2':
        seat_input = input("👉 请输入你想坐的座位号 (1-7)，直接回车则系统随机分配: ").strip()
        if seat_input.isdigit() and 1 <= int(seat_input) <= 7:
            human_seat = int(seat_input)
            print(f"✅ 你选择了专属座位：{human_seat} 号！")
        else:
            human_seat = random.randint(1, 7)
            print(f"🎲 系统已为你随机分配座位：【{human_seat}】 号！")
    elif choice == '1':
        print("✅ 已进入观战模式，请准备好瓜子。")
    else:
        print("❌ 输入无效，系统默认带你进入观战模式。")
        
    print("\n⏳ 正在连接大模型 API，准备生成对局环境...")
    time.sleep(1)

    # 发牌并装载人类/AI灵魂
    players_list = create_players(brain_map, human_seat=human_seat)
    
    # 实例化游戏引擎
    game = Game(players_list, delay_sec=delay_sec, human_seat=human_seat)

    try:
        # 正式发车！
        game.start_game()
    except KeyboardInterrupt:
        print("\n\n🚪 收到中断信号，游戏已退出。")
    except Exception as e:
        print(f"\n❌ 游戏运行中发生错误: {e}")

if __name__ == "__main__":
    main()