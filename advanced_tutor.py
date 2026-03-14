import json

def run_advanced_prediction(llm_client, chat_history, alive_seats, retriever, day=1):
    """
    高级导师预测接口：实现阶段感知检索增强（Stage-Aware RAG）。
    第1天禁用检索以规避噪音，第2天起激活检索以提升逻辑确定性。
    """
    if not isinstance(chat_history, list):
        return {str(seat): 0.0 for seat in alive_seats}
    
    # 阶段感知逻辑
    if day > 1:
        # 激活 RAG 检索
        recent_messages = chat_history[-7:]
        history_str = ""
        for msg in recent_messages:
            speech_text = msg.get("content", "")
            if len(speech_text) > 15:
                nav_title = speech_text[:20].replace('\n', ' ')
                try:
                    docs = retriever.invoke(speech_text)
                    history_str += f"\n针对近期发言【{nav_title}...】检索到的历史案底：\n"
                    for i, doc in enumerate(docs):
                        history_str += f"  - 案例{i+1}: 行为【{doc.page_content}】 -> 真实身份【{doc.metadata['role']}】\n"
                except Exception:
                    continue
        
        if not history_str:
            history_str = "暂无匹配的历史案底。"
            
        warning_msg = "核心警告（防止上下文中毒）：历史案底中可能包含平民乱玩或守卫倒钩的高噪音误导数据。请结合当前全局逻辑，批判性地参考这些案底。"
    else:
        # 第1天禁用检索，仅依赖模型原生推理
        history_str = "当前处于对局初始阶段，为了避免历史高噪音数据干扰，已禁用 RAG 战术检索。请基于当前发言进行原生逻辑推理。"
        warning_msg = "当前阶段信息熵较高，请谨慎评估各玩家发言的逻辑自洽性。"

    all_speeches = [msg.get("content", "") for msg in chat_history if isinstance(msg, dict)]
    full_context_str = "\n".join(all_speeches)

    prompt = f"""你是一个顶级的狼人杀高级导师。
当前局存活玩家座位号: {alive_seats}
当前局完整聊天记录：
{full_context_str} 

【高级战术参考库 (检索结果)】
{history_str}

【评估指令】
{warning_msg}
请结合上述信息，评估当前局所有存活玩家是狼人的概率。

严格输出纯 JSON 格式，必须包含以下两个字段：
1. "reasoning": 你的思考过程。简要分析局势，说明你如何看待历史案底（如有），并指出最可疑的玩家。
2. "probabilities": 一个字典，键为座位号(字符串)，值为 0 到 1 之间的概率(浮点数)。

示例格式：
{{
  "reasoning": "根据当前局势，X号玩家发言存在明显逻辑断层...",
  "probabilities": {{"1": 0.1, "2": 0.85}}
}}
"""
    
    messages = [{"role": "user", "content": prompt}]
    
    # 调用封装好的 send_prompt 接口
    raw_response = llm_client.send_prompt(messages, temperature=0.3, require_json=True)
    
    try:
        # 清洗并解析 JSON
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        result_json = json.loads(clean_json)
        
        # 提取概率字典
        preds = result_json.get("probabilities", {})
        
        # 容错处理：若模型未按 probabilities 嵌套，则尝试从根节点提取
        if not preds:
            preds = {k: v for k, v in result_json.items() if k != "reasoning" and isinstance(v, (int, float))}
        
        final_preds = {}
        for seat in alive_seats:
            # 默认为 0.0，确保输出完整
            final_preds[str(seat)] = float(preds.get(str(seat), 0.0))
            
        return final_preds
        
    except Exception as e:
        # 出现解析异常时返回全 0 兜底
        return {str(seat): 0.0 for seat in alive_seats}