import os
from dotenv import load_dotenv
from llm_client import LLMClient
from game import Game, create_players 

def main():
    # 1. 加载环境变量并获取密钥
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL")
    
    # 2. 初始化大语言模型客户端
    print("System: Initializing the LLM client.")
    client = LLMClient(api_key=api_key, base_url=base_url)
    
    # 3. 生成玩家并分配角色
    print("System: Creating players and assigning roles.")
    players_list = create_players(client)
    
    # 4. 实例化游戏引擎并启动主循环
    print("System: Starting the Werewolf game engine.")
    werewolf_game = Game(players_list)
    werewolf_game.start_game()

if __name__ == "__main__":
    main()