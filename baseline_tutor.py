import json
from prompts import BASELINE_TUTOR_PROMPT

def run_baseline_prediction(llm_client, chat_history, alive_seats):
    """
    执行基线预测，返回格式化的概率字典，key为seat，value为模型认为该玩家是狼人的概率
    :param llm_client: 从arena.py注入的大模型客户端
    """
    messages = [
        {"role": "system", "content": BASELINE_TUTOR_PROMPT},
        *chat_history,
        {"role": "user", "content": f"目前存活的玩家座位号是：{alive_seats}。请直接输出预测 JSON。"}
    ]
    raw_response = llm_client.send_prompt(messages, temperature=0.1, require_json=True)

    try:
        # 暴力的安全清洗，防止模型抽风带上 markdown 框
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        probabilities = json.loads(clean_json)
        return probabilities
    except Exception as e:
        print(f"  [警告] 基线探头解析 JSON 失败：{e}。原始输出：{raw_response}")
        return {}