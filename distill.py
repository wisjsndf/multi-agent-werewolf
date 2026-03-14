import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

class TacticalChunk(BaseModel):
    behavior_summary: str = Field(description="极其客观的战术行为描述，如'玩家在第一天白天划水，发言极短且不提供任何视角'。绝对不能出现具体座号！")
    ground_truth_role: str = Field(description="该玩家的真实底牌身份，如 'Villager', 'Werewolf', 'Seer' 等。")
    is_zero_information: bool = Field(description="如果是毫无逻辑的划水废话、不知道过，标记为 True；如果有具体战术意图，标记为 False。")

class GameDistillationResult(BaseModel):
    chunks: list[TacticalChunk]

def distill_game_data():
    load_dotenv()

    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL")
    )

    input_file = "rag_database.jsonl"
    output_file = "distilled_tactics.jsonl"

    print("战术提炼启动！正在读取原始对局数据...")

    with open(input_file, "r", encoding="utf-8") as f:
        games = [json.loads(line) for line in f]

    print(f"共加载了 {len(games)} 局原始数据，开始Data Distillation...\n")

    # 清空旧的提炼结果
    with open(output_file, "w", encoding="utf-8") as f:
        pass

    for i, game in enumerate(games):
        print(f"  正在提炼第 {i+1}/{len(games)} 局...", end="\r")

        prompt_content = f"""
        【任务】
        你是一个顶级的数据标注专家。请阅读以下狼人杀的白天公开聊天记录，并结合真实底牌，提取出具有代表性的玩家行为。
        
        【清洗规则】
        1. 必须去指代化：将“1号”、“3号”等具体座号，抽象为“某玩家”、“跳预言家的玩家”、“前置位玩家”等。
        2. 划水行为保留：如果玩家发言是“不知道，过”或极其奇怪的废话，请提取为“划水行为”，并将 is_zero_information 设为 true。
        3. 战术意图：提取悍跳、倒钩、带节奏等明显战术。
        
        【对局数据】
        真实底牌: {game['ground_truth']}
        公开聊天: {game['public_chat']}
        """

        try:
            # 1. 把格式要求直接写进 System Prompt 里
            system_instruction = """
            你是一个严谨的 RAG 数据提炼工程师，请严格输出 JSON 格式。
            你的输出必须是一个合法的 JSON 对象，包含一个 "chunks" 键，对应一个列表。
            列表里的每个对象必须包含以下三个字段：
            - behavior_summary (字符串类型：战术行为描述，绝不能有座号)
            - ground_truth_role (字符串类型：玩家真实底牌，如 Villager)
            - is_zero_information (布尔类型：是否为划水废话，true或false)
            """

            # 2. 退回到标准的 create 方法，并指定 type 为 json_object
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt_content}
                ],
                response_format={"type": "json_object"}, # DeepSeek 支持的标准 JSON 模式
                temperature=0.1
            )

            # 3. 手动解析返回的 JSON 字符串
            result_dict = json.loads(response.choices[0].message.content)

            with open(output_file, "a", encoding="utf-8") as out_f:
                for chunk in result_dict.get("chunks", []):
                    record = {
                        "source_game_id": game["game_id"],
                        "behavior": chunk.get("behavior_summary", ""),
                        "role": chunk.get("ground_truth_role", ""),
                        "is_zero_info": chunk.get("is_zero_information", False)
                    }
                    out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    
        except Exception as e:
            print(f"\n 第 {i+1} 局提炼失败：{e}")

    print("\n\n 提炼完成！所有战术切片已经保存至 distilled_tactics.jsonl")

if __name__ == "__main__":
    distill_game_data()