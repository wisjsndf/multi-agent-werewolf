import json
import os
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def build_vector_database():
    input_file = "distilled_tactics.jsonl"
    db_dir = "./werewolf_tactics_faiss"

    print("1. 正在读取distilled tactics...")
    documents = []

    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)

            doc = Document(
                page_content=data["behavior"],
                metadata={
                    "role": data["role"],
                    "is_zero_info": data["is_zero_info"],
                    "source_game": data.get("source_game_id", 0)
                }
            )

            documents.append(doc)

    print(f" 成功加载 {len(documents)} 条战术切片!")

    print("2. 正在初始化中文Embedding模型...")
    print(" (请耐心等待)")
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")

    print("3. 正在构建FAISS向量数据库...")
    vectorstore = FAISS.from_documents(documents, embeddings)

    print("4. 正在将数据库持久化到本地硬盘...")
    vectorstore.save_local(db_dir)

    print(f"\n 向量数据库已经成功构建并保存在 {db_dir} 文件夹下！")

    print("\n🔍 正在测试向量检索能力...")
    test_query = "有玩家在白天强行带节奏，激烈指责前置位玩家"
    print(f"\n假设当前局有人发言像这样：【{test_query}】")
    
    # 告诉 Retriever：帮我找出语义最相似的 3 条历史经验
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    results = retriever.invoke(test_query)
    
    print("\n📚 高级导师翻阅史书，找到了以下历史规律：")
    for i, res in enumerate(results):
        print(f"  案例 {i+1}: {res.page_content}")
        print(f"  👉 当时的真实底牌是: {res.metadata['role']}")
        print(f"  👉 是否为划水行为: {res.metadata['is_zero_info']}\n")

if __name__ == "__main__":
    build_vector_database()