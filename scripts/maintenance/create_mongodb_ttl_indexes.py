"""
MongoDB TTL索引创建脚本
为缓存集合添加自动过期索引，替代手动清理
"""

import os
import sys
from datetime import datetime

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:tradingagents123@localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "tradingagentscn")

COLLECTIONS_WITH_TTL = [
    "stock_data_cache",
    "fundamentals_cache",
    "news_cache",
    "financial_cache",
]


def create_ttl_indexes():
    """为MongoDB缓存集合创建TTL索引"""
    try:
        from pymongo import MongoClient
    except ImportError:
        print("❌ pymongo未安装，请运行: pip install pymongo")
        return False

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    created = 0
    skipped = 0
    errors = 0

    for collection_name in COLLECTIONS_WITH_TTL:
        collection = db[collection_name]

        try:
            existing_indexes = collection.index_information()
            ttl_index_name = "expires_at_1"

            if ttl_index_name in existing_indexes:
                print(f"⏭️  {collection_name}: TTL索引已存在，跳过")
                skipped += 1
                continue

            sample = collection.find_one()
            if sample and "expires_at" not in sample:
                print(f"⚠️  {collection_name}: 文档中无expires_at字段，需先迁移数据")
                skipped += 1
                continue

            collection.create_index(
                [("expires_at", 1)],
                name=ttl_index_name,
                expireAfterSeconds=0,
            )
            print(f"✅ {collection_name}: TTL索引创建成功")
            created += 1

        except Exception as e:
            print(f"❌ {collection_name}: TTL索引创建失败: {e}")
            errors += 1

    client.close()

    print(f"\n📊 结果: 创建={created}, 跳过={skipped}, 失败={errors}")
    return errors == 0


def migrate_expires_at():
    """将字符串格式的expires_at迁移为BSON Date类型"""
    try:
        from pymongo import MongoClient
        from dateutil.parser import parse as parse_date
    except ImportError:
        print("❌ 依赖未安装")
        return False

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    migrated = 0

    for collection_name in COLLECTIONS_WITH_TTL:
        collection = db[collection_name]

        docs = collection.find({
            "expires_at": {"$type": "string"},
        })

        for doc in docs:
            try:
                expires_str = doc["expires_at"]
                expires_dt = parse_date(expires_str)

                collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"expires_at": expires_dt}},
                )
                migrated += 1
            except Exception as e:
                print(f"⚠️ 迁移文档 {doc['_id']} 失败: {e}")

    client.close()

    print(f"📊 迁移完成: {migrated}个文档")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "migrate":
        print("🔄 迁移expires_at字段为BSON Date类型...")
        migrate_expires_at()
    else:
        print("🔄 创建MongoDB TTL索引...")
        create_ttl_indexes()
        print("\n💡 提示: 如果expires_at字段为字符串格式，先运行:")
        print(f"   python {sys.argv[0]} migrate")
