#!/usr/bin/env python3
"""
超轻量级启动脚本：不依赖重型 ML 库，仅用基础 Python 实现
"""
import sys
import os
import re
from collections import Counter

# 添加 Python path
sys.path.insert(0, os.path.dirname(__file__))

# 加载法律数据
print("📚 加载法律知识库...")
try:
    from data import load_articles
    articles = load_articles()
    print(f"✅ 已加载 {len(articles)} 条法律条文")
except Exception as e:
    print(f"❌ 加载法律数据失败: {e}")
    sys.exit(1)

# ── 简单的文本相似度计算 ──
def tokenize(text):
    """简单分词"""
    # 保留中文字符、数字、关键词
    text = text.lower()
    # 按字和词分割
    tokens = re.findall(r'[\u4e00-\u9fff]|[a-z0-9]+', text)
    return tokens

def tfidf_similarity(query_tokens, doc_tokens):
    """简单的 TF-IDF 相似度"""
    if not query_tokens or not doc_tokens:
        return 0.0
    
    query_counter = Counter(query_tokens)
    doc_counter = Counter(doc_tokens)
    
    # 计算交集
    intersection = 0
    for token in query_counter:
        if token in doc_counter:
            intersection += min(query_counter[token], doc_counter[token])
    
    # Jaccard 相似度
    union = len(set(query_tokens) | set(doc_tokens))
    if union == 0:
        return 0.0
    
    return intersection / union

def search_laws(query: str, top_k: int = 5):
    """检索相关法律条文"""
    query_tokens = tokenize(query)
    
    if not query_tokens:
        return []
    
    scores = []
    for i, article in enumerate(articles):
        full_text = f"{article['title']} {article['chapter']} {article['id']} {article['text']}"
        doc_tokens = tokenize(full_text)
        score = tfidf_similarity(query_tokens, doc_tokens)
        scores.append((i, score))
    
    # 按得分排序
    top_results = sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
    
    return [
        {
            "id": articles[i]["id"],
            "title": articles[i]["title"],
            "chapter": articles[i]["chapter"],
            "text": articles[i]["text"],
            "score": float(score)
        }
        for i, score in top_results
    ]

# ── 交互式命令行界面 ──
print("\n" + "="*60)
print("招标法律顾问 - 本地开发版")
print("="*60)
print("输入问题，系统会检索相关法律条文")
print("输入 'exit' 或 'quit' 退出")
print("="*60 + "\n")

try:
    while True:
        query = input("🤔 输入你的问题: ").strip()
        if query.lower() in ['exit', 'quit', 'q']:
            print("\n👋 再见！")
            break
        if not query:
            continue
        
        print(f"\n🔍 正在搜索相关法律条文...\n")
        results = search_laws(query, top_k=5)
        
        if results:
            for i, r in enumerate(results, 1):
                print(f"\n【{i}】{r['id']} ({r['score']:.4f})")
                print(f"    📜 {r['title']} - {r['chapter']}")
                print(f"    📋 {r['text'][:200]}..." if len(r['text']) > 200 else f"    📋 {r['text']}")
        else:
            print("❌ 未找到相关条文")
        
        print()

except KeyboardInterrupt:
    print("\n\n👋 已退出")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
