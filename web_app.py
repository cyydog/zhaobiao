#!/usr/bin/env python3
"""
网页版招标法律顾问 - 轻量级 Flask 版本
支持法律知识库搜索 + 文件上传合规审查
"""
import sys
import os
import json
from flask import Flask, render_template_string, request, jsonify
from collections import Counter
import re
from werkzeug.utils import secure_filename

# 加载法律数据
from data import load_articles

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 上传限制
app.config['UPLOAD_FOLDER'] = '/tmp/zhaobiao_uploads'

# 初始化数据
articles = load_articles()

# 创建上传目录
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def tokenize(text):
    """简单分词"""
    text = text.lower()
    tokens = re.findall(r'[\u4e00-\u9fff]|[a-z0-9]+', text)
    return tokens

def tfidf_similarity(query_tokens, doc_tokens):
    """简单的 TF-IDF 相似度"""
    if not query_tokens or not doc_tokens:
        return 0.0
    
    query_counter = Counter(query_tokens)
    doc_counter = Counter(doc_tokens)
    
    intersection = 0
    for token in query_counter:
        if token in doc_counter:
            intersection += min(query_counter[token], doc_counter[token])
    
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
    
    top_results = sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
    
    return [
        {
            "id": articles[i]["id"],
            "title": articles[i]["title"],
            "chapter": articles[i]["chapter"],
            "text": articles[i]["text"],
            "score": float(score)
        }
        for i, score in top_results if score > 0
    ]

# HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>招标法律顾问</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .tabs {
            display: flex;
            border-bottom: 2px solid #eee;
            background: #f5f5f5;
        }
        
        .tab-btn {
            flex: 1;
            padding: 16px;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            color: #999;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }
        
        .tab-btn.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        
        .tab-btn:hover {
            color: #667eea;
        }
        
        .content {
            padding: 40px;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        
        .search-box input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        .search-box input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .search-box button, .upload-btn {
            padding: 12px 32px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        
        .search-box button:hover, .upload-btn:hover {
            transform: translateY(-2px);
        }
        
        .results {
            display: none;
        }
        
        .results.show {
            display: block;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            display: none;
        }
        
        .loading.show {
            display: block;
        }
        
        .result-item {
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
            background: #f9f9f9;
            transition: all 0.3s;
        }
        
        .result-item:hover {
            border-color: #667eea;
            background: #f0f3ff;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
        }
        
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .result-id {
            font-weight: 600;
            color: #667eea;
            font-size: 16px;
        }
        
        .result-score {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .result-source {
            color: #999;
            font-size: 12px;
            margin-bottom: 10px;
        }
        
        .result-source strong {
            color: #666;
        }
        
        .result-text {
            color: #333;
            line-height: 1.6;
            font-size: 14px;
        }
        
        .no-results {
            text-align: center;
            padding: 40px 20px;
            color: #999;
        }
        
        .examples {
            background: #f0f3ff;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .examples h3 {
            font-size: 14px;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .examples ul {
            list-style: none;
        }
        
        .examples li {
            color: #666;
            font-size: 13px;
            padding: 4px 0;
        }
        
        .examples li:before {
            content: "→ ";
            color: #667eea;
            font-weight: 600;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            background: #f0f3ff;
            margin-bottom: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .upload-area:hover {
            background: #e8ecff;
        }
        
        .upload-area.dragging {
            background: #d8e0ff;
            border-color: #764ba2;
        }
        
        .upload-area p {
            color: #667eea;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        #fileInput {
            display: none;
        }
        
        .page-section {
            margin-bottom: 30px;
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 20px;
            background: #f9f9f9;
        }
        
        .page-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 16px;
            font-size: 16px;
        }
        
        .page-content {
            color: #666;
            font-size: 13px;
            line-height: 1.6;
            margin-bottom: 16px;
            padding: 12px;
            background: white;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚖️ 招标法律顾问</h1>
            <p>基于《招标投标法》及实施条例的智能合规检索工具</p>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('search')">📚 法律知识库搜索</button>
        </div>
        
        <div class="content">
            <!-- 搜索标签页 -->
            <div id="search" class="tab-content active">
                <div class="search-box">
                    <input type="text" id="queryInput" placeholder="输入你的问题（如：招标文件应该包含哪些内容）" />
                    <button onclick="search()">搜索</button>
                </div>
                
                <div class="examples">
                    <h3>📌 搜索示例：</h3>
                    <ul>
                        <li>招标文件应该包含哪些内容</li>
                        <li>投标文件有什么要求</li>
                        <li>评标过程中的禁止行为</li>
                        <li>什么情况下招标无效</li>
                        <li>开标的具体流程</li>
                    </ul>
                </div>
                
                <div id="searchLoading" class="loading">
                    <div class="spinner"></div>
                    <p style="margin-top: 20px; color: #999;">正在搜索相关法律条文...</p>
                </div>
                
                <div id="searchResults" class="results">
                    <div id="searchResultsList"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const queryInput = document.getElementById('queryInput');
        
        queryInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                search();
            }
        });
        
        function search() {
            const query = queryInput.value.trim();
            if (!query) {
                alert('请输入搜索内容');
                return;
            }
            
            const loading = document.getElementById('searchLoading');
            const results = document.getElementById('searchResults');
            const resultsList = document.getElementById('searchResultsList');
            
            loading.classList.add('show');
            results.classList.remove('show');
            
            fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                loading.classList.remove('show');
                
                if (data.results.length === 0) {
                    resultsList.innerHTML = '<div class="no-results">❌ 未找到相关条文，请尝试其他关键词</div>';
                } else {
                    resultsList.innerHTML = data.results.map((item, index) => `
                        <div class="result-item">
                            <div class="result-header">
                                <span class="result-id">【${index + 1}】${item.id}</span>
                                <span class="result-score">相关度: ${(item.score * 100).toFixed(1)}%</span>
                            </div>
                            <div class="result-source">
                                <strong>${item.title}</strong> - ${item.chapter}
                            </div>
                            <div class="result-text">${item.text}</div>
                        </div>
                    `).join('');
                }
                
                results.classList.add('show');
            })
            .catch(error => {
                loading.classList.remove('show');
                resultsList.innerHTML = '<div class="no-results">❌ 搜索出错，请重试</div>';
                results.classList.add('show');
                console.error('Error:', error);
            });
        }
    </script>
</body>
</html>
"""

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'results': []})
    
    results = search_laws(query, top_k=10)
    return jsonify({'results': results})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("招标法律顾问 - 网页版")
    print("="*60)
    print(f"✅ 已加载 {len(articles)} 条法律条文")
    print("\n🌐 访问地址: http://localhost:9090")
    print("="*60 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=9090)
