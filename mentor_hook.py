from mentor.graph_builder import mentor_graph

def get_human_input_with_mentor(game_instance, human_player, stage_name, prompt_text):
    """万能输入拦截器：检测 /mentor 命令并呼叫导师"""
    while True:
        user_input = input(f"{prompt_text} (求助导师请加 /mentor): ").strip()
        
        if user_input.startswith("/mentor"):
            question = user_input.replace("/mentor", "").strip()
            if not question:
                print("💡 导师：请告诉我具体的问题，比如 '/mentor 我现在该投谁'")
                continue
            
            print("\n⏳ 导师正在快速翻阅规则与局势记录，请稍候...")
            
            # 组装安全字典供导师查阅
            chat_str = "\n".join([msg["content"] for msg in game_instance.public_chat_history])
            alive_seats = [p.seat for p in game_instance.players.values() if p.is_alive]
            night_record = human_player.get_private_state()

            safe_state = {
                "human_question": question,
                "current_day": game_instance.day_count,
                "stage": stage_name,
                "alive_players": alive_seats,
                "my_role": human_player.role,
                "my_night_record": night_record,
                "short_term_memory": chat_str
            }
            
            try:
                result = mentor_graph.invoke(safe_state)
                print("\n" + "="*50)
                print(f"💡 【导师战术板】:\n{result.get('final_answer', '系统异常，导师沉默。')}")
                print("="*50 + "\n")
            except Exception as e:
                print(f"❌ 导师系统开小差了: {e}\n")
        else:
            return user_input