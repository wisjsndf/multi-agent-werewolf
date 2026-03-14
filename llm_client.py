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

    def send_prompt(self, messages, temperature=0.7, require_json=False):
        """
        核心方法：发送消息列表并获取大模型的回复内容
        :param require_json: 如果为 True，将物理强制大模型只输出合法的 JSON 格式。
        """
        max_retries = 3
        safe_messages = self._clean_messages(messages)

        # 动态拼装请求参数
        request_kwargs = {
            "model": self.model_name,
            "messages": safe_messages,
            "temperature": temperature,
        }

        if require_json:
            request_kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(max_retries):
            try:
                # 使用 **字典解包 的方式把参数传进去
                response = self.client.chat.completions.create(**request_kwargs)
                return response.choices[0].message.content
            
            except Exception as e:
                print(f"  [网络警告] API 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print("  [错误] 达到最大重试次数。")
                    return "{}" if require_json else "（思考失败，本轮选择过麦）"