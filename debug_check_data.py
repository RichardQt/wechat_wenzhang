#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
诊断脚本 - 检查数据库中的普法文章数据
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database import DatabaseManager
import json

# 加载配置
with open('reading_updater_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

db = DatabaseManager(
    host=config['database']['host'],
    port=config['database']['port'],
    user=config['database']['user'],
    password=config['database']['password'],
    database=config['database']['database']
)

if not db.connect():
    print("❌ 数据库连接失败")
    sys.exit(1)

print("=" * 70)
print("📊 数据库诊断检查")
print("=" * 70)
print()

try:
    with db.connection.cursor() as cursor:
        # 1. 检查 fx_article_records 表中近7天的文章总数
        print("1️⃣ 检查 fx_article_records 表近7天的文章...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        sql = """
        SELECT COUNT(*) as count
        FROM fx_article_records
        WHERE publish_time >= %s AND publish_time <= %s
        """
        cursor.execute(sql, (start_date, end_date))
        result = cursor.fetchone()
        print(f"   近7天文章总数: {result['count']} 篇")
        print()
        
        # 2. 检查 fx_education_articles 表中的普法文章
        print("2️⃣ 检查 fx_education_articles 表中的普法文章...")
        sql = """
        SELECT type_class, COUNT(*) as count
        FROM fx_education_articles
        GROUP BY type_class
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        print("   按类型统计:")
        for row in results:
            type_name = "普法文章" if row['type_class'] == '1' else f"其他类型({row['type_class']})"
            print(f"   - {type_name}: {row['count']} 篇")
        print()
        
        # 3. 检查近7天的普法文章（JOIN查询）
        print("3️⃣ 检查近7天的普法文章（关联查询）...")
        sql = """
        SELECT COUNT(*) as count
        FROM fx_article_records ar
        INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
        WHERE ea.type_class = '1'
          AND ar.publish_time >= %s
          AND ar.publish_time <= %s
        """
        cursor.execute(sql, (start_date, end_date))
        result = cursor.fetchone()
        print(f"   近7天普法文章数: {result['count']} 篇")
        print()
        
        # 4. 检查有URL的普法文章
        print("4️⃣ 检查近7天有URL的普法文章...")
        sql = """
        SELECT COUNT(*) as count
        FROM fx_article_records ar
        INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
        WHERE ea.type_class = '1'
          AND ar.publish_time >= %s
          AND ar.publish_time <= %s
          AND ar.article_url IS NOT NULL
          AND ar.article_url != ''
        """
        cursor.execute(sql, (start_date, end_date))
        result = cursor.fetchone()
        print(f"   有URL的普法文章数: {result['count']} 篇")
        print()
        
        # 5. 查看最近的几篇文章详情
        print("5️⃣ 查看最近的5篇文章详情...")
        sql = """
        SELECT 
            ar.article_id,
            ar.article_title,
            ar.publish_time,
            ar.article_url,
            ea.type_class
        FROM fx_article_records ar
        LEFT JOIN fx_education_articles ea ON ar.article_id = ea.article_id
        ORDER BY ar.publish_time DESC
        LIMIT 5
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if results:
            for i, row in enumerate(results, 1):
                print(f"   {i}. 文章ID: {row['article_id']}")
                print(f"      标题: {row['article_title'][:50]}...")
                print(f"      发布时间: {row['publish_time']}")
                print(f"      类型: {row['type_class'] or '未分类'}")
                print(f"      有URL: {'是' if row['article_url'] else '否'}")
                print()
        else:
            print("   ❌ 没有找到任何文章")
        
        # 6. 检查 type_class = '1' 的文章发布时间分布
        print("6️⃣ 检查普法文章的发布时间分布...")
        sql = """
        SELECT 
            DATE(ar.publish_time) as date,
            COUNT(*) as count
        FROM fx_article_records ar
        INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
        WHERE ea.type_class = '1'
        GROUP BY DATE(ar.publish_time)
        ORDER BY date DESC
        LIMIT 10
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if results:
            print("   最近10天的普法文章数量:")
            for row in results:
                print(f"   - {row['date']}: {row['count']} 篇")
        else:
            print("   ❌ 没有找到普法文章")
        
        print()
        print("=" * 70)
        print("✅ 诊断完成")
        print("=" * 70)
        
finally:
    db.disconnect()
