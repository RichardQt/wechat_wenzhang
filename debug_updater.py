#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
诊断 manual_reading_update.py 的问题
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from article_reading_updater import ArticleReadingUpdater
from spider.log.utils import logger

print("=" * 70)
print("🔍 诊断 ArticleReadingUpdater 问题")
print("=" * 70)
print()

# 创建更新器
print("1️⃣ 创建 ArticleReadingUpdater 实例...")
updater = ArticleReadingUpdater("reading_updater_config.json")
print(f"   ✅ 实例创建成功")
print(f"   数据库连接对象: {updater.db}")
print(f"   数据库连接状态: {updater.db.connection}")
print()

# 测试1：不连接直接查询
print("2️⃣ 测试：不连接数据库直接查询...")
articles = updater.get_articles_need_update(7)
print(f"   查询结果: {len(articles)} 篇")
print()

# 测试2：先连接再查询
print("3️⃣ 测试：先连接数据库再查询...")
if updater.db.connect():
    print("   ✅ 数据库连接成功")
    print(f"   连接状态: {updater.db.connection}")
    articles = updater.get_articles_need_update(7)
    print(f"   查询结果: {len(articles)} 篇")
    
    if articles:
        print(f"\n   前3篇文章:")
        for i, article in enumerate(articles[:3], 1):
            print(f"   {i}. {article['article_title'][:50]}")
    
    updater.db.disconnect()
else:
    print("   ❌ 数据库连接失败")

print()
print("=" * 70)
print("✅ 诊断完成")
print("=" * 70)
