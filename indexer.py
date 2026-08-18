"""
索引模块：启动时将招标法条文索引到 Qdrant
幂等设计：若 collection 已存在且条文数量匹配，则跳过
"""

import os
import sys
import time
import logging

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

from data import get_all_articles, get_article_count
from retriever import LAW_COLLECTION as COLLECTION_NAME, EMBEDDING_MODEL, EMBEDDING_DIM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 32


def connect_qdrant():
    """连接 Qdrant（支持远程/内存/本地路径三种模式，无需 Docker）"""
    if os.getenv("QDRANT_HOST") == ":memory:":
        logger.info("使用 Qdrant 内存模式")
        return QdrantClient(":memory:")
    if os.getenv("QDRANT_PATH"):
        logger.info(f"使用 Qdrant 本地路径模式: {os.getenv('QDRANT_PATH')}")
        return QdrantClient(path=os.getenv("QDRANT_PATH"))

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    logger.info(f"连接 Qdrant 服务: {host}:{port}")

    client = QdrantClient(host=host, port=port)
    for i in range(30):
        try:
            client.get_collections()
            logger.info("Qdrant 服务已就绪")
            return client
        except Exception as e:
            logger.info(f"等待 Qdrant 就绪... ({i+1}/30): {e}")
            time.sleep(2)
    logger.error("Qdrant 服务未能在规定时间内启动，退出")
    sys.exit(1)


def index_articles(client: QdrantClient, model: SentenceTransformer):
    """将所有条文编码并索引到 Qdrant"""
    articles = get_all_articles()
    total = len(articles)
    logger.info(f"开始索引 {total} 条法律条文...")

    # 检查 collection 是否已存在且数量匹配
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        count = client.count(collection_name=COLLECTION_NAME).count
        if count == total:
            logger.info(f"Collection '{COLLECTION_NAME}' 已存在（{count} 条），跳过索引")
            return
        else:
            logger.info(f"Collection 存在但条数不匹配（{count} vs {total}），重建...")
            client.delete_collection(COLLECTION_NAME)

    # 创建 collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
    )
    logger.info(f"已创建 collection: {COLLECTION_NAME}")

    # 批量编码并上传
    points = []
    texts_for_encode = []

    for article in articles:
        # 拼接法律名称+章节+条号+内容，提升语义质量
        full_text = f"{article.get('title', '')} {article['chapter']} {article['id']} {article['text']}"
        texts_for_encode.append(full_text)

    logger.info("正在生成 embeddings（首次启动需要下载模型，请稍候）...")
    vectors = model.encode(
        texts_for_encode,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    for idx, (article, vector) in enumerate(zip(articles, vectors)):
        points.append(
            PointStruct(
                id=idx,
                vector=vector.tolist(),
                payload={
                    "id": article["id"],
                    "title": article.get("title", ""),
                    "chapter": article["chapter"],
                    "text": article["text"],
                },
            )
        )

    # 批量上传
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i: i + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)

    logger.info(f"索引完成，共 {len(points)} 条条文已写入 Qdrant")


def main():
    client = connect_qdrant()

    logger.info(f"加载 Embedding 模型: {EMBEDDING_MODEL}")
    model = SentenceTransformer(EMBEDDING_MODEL)

    index_articles(client, model)


if __name__ == "__main__":
    main()
