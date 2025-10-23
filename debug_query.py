#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试查询逻辑
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

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
print("🔍 测试查询逻辑")
print("=" * 70)

days = 7
end_date = datetime.now()
start_date = end_date - timedelta(days=days)

print(f"当前时间: {end_date}")
print(f"开始时间: {start_date}")
print(f"结束时间: {end_date}")
print()

try:
    with db.connection.cursor() as cursor:
        # 使用完全相同的查询
        sql = """
        SELECT 
            ar.id,
            ar.article_id,
            ar.article_title,
            ar.article_url,
            ar.publish_time,
            ar.unit_name,
            ar.view_count,
            ar.likes,
            ar.thumbs_count,
            ea.type_class
        FROM fx_article_records ar
        INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
        WHERE ea.type_class = '1'
          AND ar.publish_time >= %s
          AND ar.publish_time <= %s
          AND ar.article_url IS NOT NULL 
          AND ar.article_url != ''
        ORDER BY ar.publish_time DESC
        """
        
        print(f"执行SQL查询...")
        print(f"参数: start_date={start_date}, end_date={end_date}")
        print()
        
        cursor.execute(sql, (start_date, end_date))
        articles = cursor.fetchall()
        
        print(f"查询结果: {len(articles)} 篇")
        print()
        
        if articles:
            print("前5篇文章:")
            for i, article in enumerate(articles[:5], 1):
                print(f"{i}. {article['article_title'][:50]}")
                print(f"   发布时间: {article['publish_time']}")
                print(f"   单位: {article['unit_name']}")
                print()
        else:
            print("❌ 没有查询到任何文章")
            print()
            print("再次检查条件...")
            
            # 分步检查
            sql1 = "SELECT COUNT(*) as cnt FROM fx_article_records WHERE publish_time >= %s AND publish_time <= %s"
            cursor.execute(sql1, (start_date, end_date))
            r1 = cursor.fetchone()
            print(f"1. 时间范围内的文章总数: {r1['cnt']}")
            
            sql2 = "SELECT COUNT(*) as cnt FROM fx_education_articles WHERE type_class = '1'"
            cursor.execute(sql2)
            r2 = cursor.fetchone()
            print(f"2. 普法文章总数: {r2['cnt']}")
            
            sql3 = """
            SELECT COUNT(*) as cnt 
            FROM fx_article_records ar
            INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
            WHERE ea.type_class = '1'
            """
            cursor.execute(sql3)
            r3 = cursor.fetchone()
            print(f"3. 关联后的普法文章总数: {r3['cnt']}")
            
            sql4 = """
            SELECT COUNT(*) as cnt 
            FROM fx_article_records ar
            INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
            WHERE ea.type_class = '1'
              AND ar.publish_time >= %s
              AND ar.publish_time <= %s
            """
            cursor.execute(sql4, (start_date, end_date))
            r4 = cursor.fetchone()
            print(f"4. 时间范围内的普法文章: {r4['cnt']}")
            
            sql5 = """
            SELECT COUNT(*) as cnt 
            FROM fx_article_records ar
            INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
            WHERE ea.type_class = '1'
              AND ar.publish_time >= %s
              AND ar.publish_time <= %s
              AND ar.article_url IS NOT NULL
            """
            cursor.execute(sql5, (start_date, end_date))
            r5 = cursor.fetchone()
            print(f"5. 有URL的普法文章: {r5['cnt']}")
            
            sql6 = """
            SELECT COUNT(*) as cnt 
            FROM fx_article_records ar
            INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
            WHERE ea.type_class = '1'
              AND ar.publish_time >= %s
              AND ar.publish_time <= %s
              AND ar.article_url IS NOT NULL
              AND ar.article_url != ''
            """
            cursor.execute(sql6, (start_date, end_date))
            r6 = cursor.fetchone()
            print(f"6. URL不为空的普法文章: {r6['cnt']}")

finally:
    db.disconnect()
