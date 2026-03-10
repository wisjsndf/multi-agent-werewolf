import os
from dotenv import load_dotenv
from llm_client import LLMClient
from game_objects import Villager
import prompts

# 1. 加载环境变量
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL")

# 2. 启动通讯员
print("正在连接大模型...")
client = LLMClient(api_key=api_key, base_url=base_url)

# 3. 创建一个 3号 平民玩家
player3 = Villager(seat=3, llm_client=client)

# 4. 模拟一段极其简单的历史记录和场景
mock_history = [
    {"role": "user", "content": "上帝宣布：天亮了，昨晚是平安夜。请 3 号玩家发言。"}
]

# 5. 点火！让 3号 平民说话
print("\n测试开始，等待 3号 发言...")
reply = player3.speak(mock_history, prompts.VILLAGER_DAY_SPEAK)

print("\n=== 3号玩家的回复 ===")
print(reply)