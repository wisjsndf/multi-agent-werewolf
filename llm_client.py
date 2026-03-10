from openai import OpenAI
import time

class LLMClient:
    def __init__(self, api_key, base_url, model_name="deepseek-chat"):
        """
        初始化大模型客户端
        :param api_key: 你的 API 密钥
        :param base_url: API 请求的基础地址
        :param model_name: 使用的模型名称 (默认使用 DeepSeek 的对话模型)
        """
        self.model_name = model_name

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def _clean_messages(self, messages):
        """
        🛡️ 异构模型兼容层：消息清洗器
        确保除了第 0 个位置，后面绝对不出现 'role': 'system'
        """
        cleaned = []
        for i, msg in enumerate(messages):
            # 如果是 system 角色，且不是放在列表的第一位
            if msg["role"] == "system" and i != 0:
                # 极其温柔地把它降级为带标签的 user 消息
                cleaned.append({
                    "role": "user", 
                    "content": f"【上帝/系统广播】：{msg['content']}"
                })
            else:
                # 第一位的 system 或者是正常的 user 消息，原样保留
                cleaned.append(msg)
        return cleaned

    def send_prompt(self, messages, temperature=0.7):
        """
        核心方法：发送消息列表并获取大模型的回复内容
        :param messages: 消息列表，格式为 [{"role": "system", "content": "..."}, ...]
        :param temperature: 随机性/创造力指数。数值越高，回复越多样化；数值越低，回复越确定。
        :return: 字符串 (AI 的回复文本)
        """
        max_retries = 3

        safe_messages = self._clean_messages(messages)

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=safe_messages,
                    temperature=temperature,
                )

                reply_text = response.choices[0].message.content
                return reply_text
            
            except Exception as e:
                print(f"  [网络警告] API 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2) # 失败后等 2 秒再试
                else:
                    print("  [错误] 达到最大重试次数，该玩家本轮沉默。")
                    return "（思考失败，本轮选择过麦）"