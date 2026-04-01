import os
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI

load_dotenv(find_dotenv())

def get_mentor_llm(temperature: float = 0.0) -> ChatOpenAI:
    llm = ChatOpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
        model="deepseek-chat",
        temperature=temperature
    )

    print("LLM instance loaded.")
    return llm

if __name__ == "__main__":
    test_llm = get_mentor_llm()
    print("Test mode completed.")