#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
手动更新阅读量脚本
================

手动更新近N天所有普法文章的阅读量等信息
支持命令行参数指定天数
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from article_reading_updater import ArticleReadingUpdater
from spider.log.utils import logger


def print_banner():
    """打印程序标题"""
    print("=" * 70)
    print("📊 微信公众号文章阅读量手动更新工具")
    print("=" * 70)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def preview_articles(updater: ArticleReadingUpdater, days: int):
    """
    预览待更新的文章列表
    
    Args:
        updater: 更新器实例
        days: 检查的天数
    """
    logger.info(f"🔍 正在查询近 {days} 天需要更新的普法文章...")
    
    if not updater.db.connect():
        logger.error("❌ 数据库连接失败")
        return False
    
    try:
        articles = updater.get_articles_need_update(days)
        
        if not articles:
            logger.info("✅ 没有需要更新的文章")
            print("\n" + "=" * 70)
            print("📋 查询结果: 没有找到需要更新的文章")
            print("=" * 70)
            return True
        
        # 显示统计信息
        print("\n" + "=" * 70)
        print(f"📋 找到 {len(articles)} 篇需要更新的普法文章")
        print("=" * 70)
        
        # 显示文章列表（显示前20篇）
        display_count = min(20, len(articles))
        print(f"\n前 {display_count} 篇文章详情:\n")
        
        for i, article in enumerate(articles[:display_count], 1):
            publish_time = article['publish_time'].strftime('%Y-%m-%d %H:%M')
            title = article['article_title']
            unit_name = article.get('unit_name', '未知单位')
            
            # 显示当前数据
            view_count = article.get('view_count', 0) or 0
            likes = article.get('likes', 0) or 0
            thumbs_count = article.get('thumbs_count', 0) or 0
            
            # 格式化输出
            if len(title) > 45:
                title = title[:45] + "..."
            
            print(f"{i:2d}. {title}")
            print(f"    单位: {unit_name}")
            print(f"    发布时间: {publish_time}")
            print(f"    当前数据: 阅读{view_count} | 在看{likes} | 点赞{thumbs_count}")
            print()
        
        if len(articles) > display_count:
            print(f"... 还有 {len(articles) - display_count} 篇文章未显示")
            print()
        
        print("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 预览文章列表时出错: {e}")
        return False
    finally:
        updater.db.disconnect()


def manual_update(updater: ArticleReadingUpdater, days: int, preview_only: bool = False):
    """
    执行手动更新
    
    Args:
        updater: 更新器实例
        days: 检查的天数
        preview_only: 是否仅预览
    """
    # 临时修改检查天数
    original_days = updater.days_to_check
    updater.days_to_check = days
    
    try:
        if preview_only:
            # 仅预览模式
            return preview_articles(updater, days)
        
        # 执行更新前先查询文章数量
        logger.info(f"📋 更新范围: 近 {days} 天的普法文章")
        
        # 连接数据库查询文章列表
        if not updater.db.connect():
            logger.error("❌ 数据库连接失败")
            return False
        
        try:
            articles = updater.get_articles_need_update(days)
            
            # 注意：这里不断开连接，因为 run_update() 需要使用
            
            if not articles:
                logger.info("✅ 没有需要更新的文章")
                updater.db.disconnect()
                return True
            
            # 显示待更新文章数量
            print(f"\n找到 {len(articles)} 篇需要更新的文章")
            
            # 询问是否继续
            response = input(f"\n是否继续更新这些文章? (y/n): ").strip().lower()
            if response != 'y' and response != 'yes':
                logger.info("❌ 用户取消更新操作")
                updater.db.disconnect()
                return False
            
        except Exception as e:
            logger.error(f"❌ 查询文章列表时出错: {e}")
            updater.db.disconnect()
            return False
        
        # 断开连接，让 run_update() 自己管理连接
        updater.db.disconnect()
        
        # 执行更新
        logger.info("🚀 开始执行更新任务...")
        print("\n" + "=" * 70)
        
        success = updater.run_update()
        
        if success:
            logger.success("✅ 更新任务执行成功")
            return True
        else:
            logger.error("❌ 更新任务执行失败")
            return False
            
    finally:
        # 恢复原始天数设置
        updater.days_to_check = original_days


def show_statistics(updater: ArticleReadingUpdater, days: int):
    """
    显示统计信息
    
    Args:
        updater: 更新器实例
        days: 统计的天数
    """
    logger.info(f"📊 正在统计近 {days} 天的数据...")
    
    stats = updater.get_update_statistics(days)
    
    if not stats:
        logger.error("❌ 无法获取统计信息")
        return False
    
    print("\n" + "=" * 70)
    print(f"📈 近 {days} 天普法文章阅读量统计")
    print("=" * 70)
    print(f"总文章数量: {stats['total_articles']} 篇")
    print(f"已更新数量: {stats['updated_articles']} 篇")
    print(f"待更新数量: {stats['need_update_articles']} 篇")
    print(f"完成率: {stats['completion_rate']}%")
    print(f"统计时间: {stats['date_range']['start_date']} 至 {stats['date_range']['end_date']}")
    print("=" * 70)
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="手动更新微信公众号文章阅读量工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                          # 更新近7天的普法文章（默认）
  %(prog)s -d 3                     # 更新近3天的普法文章
  %(prog)s -d 14                    # 更新近14天的普法文章
  %(prog)s -d 7 --preview           # 仅预览近7天待更新的文章列表
  %(prog)s -d 7 --stats             # 显示近7天的统计信息
  %(prog)s --config my_config.json  # 使用自定义配置文件

说明:
  - 默认更新近7天的普法文章
  - 使用 -d 或 --days 参数可以指定天数
  - 使用 --preview 参数可以先预览待更新的文章列表，不实际更新
  - 使用 --stats 参数可以查看统计信息
        """
    )
    
    # 基本参数
    parser.add_argument(
        "-d", "--days",
        type=int,
        default=7,
        help="要检查的天数 (默认: 7天)"
    )
    
    parser.add_argument(
        "--config",
        default="reading_updater_config.json",
        help="配置文件路径 (默认: reading_updater_config.json)"
    )
    
    # 操作模式
    parser.add_argument(
        "--preview",
        action="store_true",
        help="仅预览待更新文章列表，不执行实际更新"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示统计信息"
    )
    
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="跳过确认提示，直接执行更新"
    )
    
    args = parser.parse_args()
    
    # 打印标题
    print_banner()
    
    # 检查配置文件
    if not os.path.exists(args.config):
        logger.error(f"❌ 配置文件不存在: {args.config}")
        logger.info("💡 请确保配置文件存在或使用 --config 参数指定配置文件路径")
        return 1
    
    # 验证天数参数
    if args.days <= 0:
        logger.error("❌ 天数参数必须大于0")
        return 1
    
    if args.days > 365:
        logger.warning("⚠️  天数参数过大，建议不超过365天")
        response = input("是否继续? (y/n): ").strip().lower()
        if response != 'y' and response != 'yes':
            return 0
    
    # 创建更新器
    try:
        updater = ArticleReadingUpdater(args.config)
        logger.info(f"✅ 配置文件加载成功: {args.config}")
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return 1
    
    # 根据模式执行对应功能
    try:
        if args.stats:
            # 显示统计信息
            success = show_statistics(updater, args.days)
        elif args.preview:
            # 仅预览
            success = preview_articles(updater, args.days)
        else:
            # 执行更新（如果指定了-y参数，则跳过确认）
            if args.yes:
                # 直接执行更新，不询问确认
                logger.info(f"🚀 自动模式: 开始更新近 {args.days} 天的普法文章...")
                updater.days_to_check = args.days
                success = updater.run_update()
            else:
                # 正常模式，需要用户确认
                success = manual_update(updater, args.days, preview_only=False)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n")
        logger.info("⚠️  用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"❌ 程序执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
