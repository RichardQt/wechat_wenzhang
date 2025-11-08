#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
阅读量更新系统启动脚本
==================

统一入口脚本，提供多种运行模式
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from article_reading_updater import ArticleReadingUpdater
from reading_update_scheduler import ReadingUpdateScheduler
from theme_reading_updater import ThemeReadingUpdater
from spider.log.utils import logger


def print_banner():
    """打印程序标题"""
    print("=" * 60)
    print("📊 微信公众号文章阅读量更新系统")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def run_immediate_update(config_file: str, days: int = None):
    """立即执行更新任务"""
    logger.info("🚀 立即执行模式")
    
    updater = ArticleReadingUpdater(config_file)
    
    if days:
        # 临时修改检查天数
        updater.days_to_check = days
        logger.info(f"临时设置检查天数为: {days}")
    
    success = updater.run_update()
    
    if success:
        logger.success("✅ 更新任务执行成功")
        return 0
    else:
        logger.error("❌ 更新任务执行失败")
        return 1


def run_scheduler(config_file: str, hour: int = 18, minute: int = 30):
    """运行定时调度器"""
    logger.info("⏰ 定时调度器模式")
    
    scheduler = ReadingUpdateScheduler(config_file)
    
    try:
        scheduler.start(hour, minute)
        return 0
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"调度器运行异常: {e}")
        return 1


def show_statistics(config_file: str, days: int = 7):
    """显示统计信息"""
    logger.info("📊 统计信息模式")
    
    updater = ArticleReadingUpdater(config_file)
    stats = updater.get_update_statistics(days)
    
    if not stats:
        logger.error("无法获取统计信息")
        return 1
    
    print("\n" + "=" * 50)
    print(f"📈 近{days}天普法文章阅读量统计")
    print("=" * 50)
    print(f"总文章数量: {stats['total_articles']}")
    print(f"已更新数量: {stats['updated_articles']}")
    print(f"待更新数量: {stats['need_update_articles']}")
    print(f"完成率: {stats['completion_rate']}%")
    print(f"统计时间范围: {stats['date_range']['start_date']} 到 {stats['date_range']['end_date']}")
    print("=" * 50)
    
    return 0


def test_api_connection(config_file: str):
    """测试API连接"""
    logger.info("🔗 API连接测试模式")
    
    try:
        from dsf_api_client import DSFApiClient
        import json
        
        # 加载配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        api_config = config.get('api', {})
        api_key = api_config.get('key', '')
        
        if not api_key or api_key == 'your_api_key_here':
            logger.error("请先在配置文件中设置正确的API密钥")
            return 1
        
        # 创建API客户端
        client = DSFApiClient(
            api_key=api_key,
            verify_code=api_config.get('verify_code', ''),
            base_url=api_config.get('base_url', 'https://www.dajiala.com')
        )
        
        # 使用示例URL测试
        test_url = "https://mp.weixin.qq.com/s?__biz=MjM5MTM5NjUzNA==&mid=2652494556&idx=1&sn=4995d845ad2ef1205136936f65ae4adc"
        
        logger.info(f"测试API连接...")
        success, data, error = client.get_article_stats(test_url)
        
        if success:
            logger.success("✅ API连接测试成功")
            logger.info(f"测试结果: 阅读{data['read']} 点赞{data['zan']} 在看{data['looking']}")
            return 0
        else:
            logger.error(f"❌ API连接测试失败: {error}")
            return 1
            
    except Exception as e:
        logger.error(f"API测试异常: {e}")
        return 1


def check_theme_end(config_file: str):
    """检查明天是否有法律主题结束"""
    logger.info("🎯 法律主题检查模式")
    
    updater = ThemeReadingUpdater(config_file)
    
    if not updater.db.connect():
        logger.error("数据库连接失败")
        return 1
    
    try:
        theme = updater.get_upcoming_theme_end()
        
        if theme:
            print("\n" + "="*60)
            print("✅ 明天是法律主题结束日")
            print("="*60)
            print(f"主题名称: {theme['theme_name']}")
            print(f"主题年份: {theme['year']}")
            print(f"开始日期: {theme['start_date']}")
            print(f"结束日期: {theme['end_date']}")
            print(f"主题ID: {theme['id']}")
            print(f"报告生成: {'已生成' if theme['is_generated'] else '未生成'}")
            print("="*60)
            
            # 计算主题天数
            days = (theme['end_date'] - theme['start_date']).days + 1
            print(f"\n📅 主题持续时间: {days} 天")
            print(f"💡 将更新该期间内所有普法文章的阅读量")
            
            return 0
        else:
            print("\n" + "="*60)
            print("❌ 明天不是任何法律主题的结束日")
            print("="*60)
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"明天日期: {tomorrow}")
            print("无需执行法律主题更新任务")
            print("="*60)
            return 0
            
    finally:
        updater.db.disconnect()


def run_theme_update(config_file: str, theme_id: int = None):
    """执行法律主题阅读量更新"""
    logger.info("🎯 法律主题更新模式")
    
    updater = ThemeReadingUpdater(config_file)
    
    if theme_id:
        logger.info(f"强制更新主题ID: {theme_id}")
    
    success = updater.run_theme_update(force_theme_id=theme_id)
    
    if success:
        logger.success("✅ 法律主题更新任务执行成功")
        return 0
    else:
        logger.error("❌ 法律主题更新任务执行失败")
        return 1


def list_themes(config_file: str):
    """列出所有活动的法律主题"""
    logger.info("📋 法律主题列表模式")
    
    updater = ThemeReadingUpdater(config_file)
    themes = updater.list_active_themes()
    
    if not themes:
        print("\n没有找到活动中的法律主题")
        return 0
    
    print("\n" + "="*100)
    print("📋 活动中的法律主题")
    print("="*100)
    print(f"{'ID':<5} {'年份':<6} {'主题名称':<40} {'开始日期':<12} {'结束日期':<12} {'报告':<6}")
    print("-"*100)
    
    for theme in themes:
        theme_id = theme['id']
        year = theme['year']
        name = theme['theme_name'][:38] + '...' if len(theme['theme_name']) > 40 else theme['theme_name']
        start = str(theme['start_date'])
        end = str(theme['end_date'])
        generated = '已生成' if theme['is_generated'] else '未生成'
        
        print(f"{theme_id:<5} {year:<6} {name:<40} {start:<12} {end:<12} {generated:<6}")
    
    print("="*100)
    print(f"共 {len(themes)} 个活动主题\n")
    
    return 0


def dry_run(config_file: str, days: int = None):
    """试运行模式"""
    logger.info("🔍 试运行模式 - 只查询不更新")
    
    updater = ArticleReadingUpdater(config_file)
    
    if not updater.db.connect():
        logger.error("数据库连接失败")
        return 1
    
    try:
        # 第一步：获取近N天阅读量为空的文章
        logger.info("\n" + "="*50)
        logger.info("📝 第一步：查询近7天内阅读量为空的文章")
        logger.info("="*50)
        empty_articles = updater.get_articles_need_update(days, only_empty=True)
        
        # 第二步：获取前6天的文章
        six_days_ago = datetime.now() - timedelta(days=6)
        logger.info("\n" + "="*50)
        logger.info(f"📅 第二步：查询往前推6天的文章 (发布日期: {six_days_ago.strftime('%Y-%m-%d')})")
        logger.info("="*50)
        six_days_ago_articles = updater.get_articles_for_specific_day(six_days_ago)
        
        # 合并并去重
        all_articles = empty_articles.copy() if empty_articles else []
        existing_article_ids = {article['article_id'] for article in all_articles}
        
        additional_count = 0
        for article in six_days_ago_articles:
            if article['article_id'] not in existing_article_ids:
                all_articles.append(article)
                existing_article_ids.add(article['article_id'])
                additional_count += 1
        
        if not all_articles:
            logger.info("\n没有需要更新的文章")
            return 0
        
        logger.info("\n" + "="*50)
        logger.info("📊 更新任务汇总")
        logger.info("="*50)
        logger.info(f"近{days if days else updater.days_to_check}天阅读量为空: {len(empty_articles)} 篇")
        logger.info(f"往前推6天({six_days_ago.strftime('%Y-%m-%d')}): {len(six_days_ago_articles)} 篇")
        logger.info(f"去重后实际需要更新: {len(all_articles)} 篇")
        logger.info(f"  - 其中来自近7天为空: {len(empty_articles)} 篇")
        logger.info(f"  - 其中来自前6天额外: {additional_count} 篇")
        logger.info("")
        
        # 显示前10篇文章信息
        logger.info("前10篇待更新文章:")
        for i, article in enumerate(all_articles[:10], 1):
            publish_time = article['publish_time'].strftime('%Y-%m-%d %H:%M')
            title = article['article_title'][:40] + "..." if len(article['article_title']) > 40 else article['article_title']
            has_data = "有数据" if article.get('view_count') is not None else "为空"
            logger.info(f"  {i:2d}. {title} ({publish_time}) [{has_data}] - {article['unit_name']}")
        
        if len(all_articles) > 10:
            logger.info(f"  ... 还有 {len(all_articles) - 10} 篇文章")
        
        return 0
        
    finally:
        updater.db.disconnect()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="微信公众号文章阅读量更新系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --now                    # 立即执行更新任务
  %(prog)s --schedule               # 启动定时调度器(每天6:00执行)
  %(prog)s --schedule --hour 8      # 启动定时调度器(每天8:00执行)
  %(prog)s --stats                  # 显示统计信息
  %(prog)s --stats --days 14        # 显示近14天统计信息
  %(prog)s --test-api               # 测试API连接
  %(prog)s --dry-run                # 试运行(只查询不更新)
  %(prog)s --dry-run --days 3       # 试运行查询近3天文章
  %(prog)s --check-theme            # 检查明天是否有法律主题结束
  %(prog)s --theme-update           # 执行法律主题更新任务
  %(prog)s --theme-update --theme-id 10  # 强制更新指定主题
  %(prog)s --list-themes            # 列出所有活动的法律主题
        """
    )
    
    # 运行模式选项
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--now", action="store_true", help="立即执行更新任务")
    mode_group.add_argument("--schedule", action="store_true", help="启动定时调度器")
    mode_group.add_argument("--stats", action="store_true", help="显示统计信息")
    mode_group.add_argument("--test-api", action="store_true", help="测试API连接")
    mode_group.add_argument("--dry-run", action="store_true", help="试运行模式(只查询不更新)")
    mode_group.add_argument("--check-theme", action="store_true", help="检查明天是否有法律主题结束")
    mode_group.add_argument("--theme-update", action="store_true", help="执行法律主题阅读量更新")
    mode_group.add_argument("--list-themes", action="store_true", help="列出所有活动的法律主题")
    
    # 通用选项
    parser.add_argument("--config", default="reading_updater_config.json", help="配置文件路径")
    parser.add_argument("--days", type=int, help="检查的天数")
    
    # 调度器选项
    parser.add_argument("--hour", type=int, default=6, help="定时执行的小时 (0-23)")
    parser.add_argument("--minute", type=int, default=0, help="定时执行的分钟 (0-59)")
    
    # 法律主题选项
    parser.add_argument("--theme-id", type=int, help="强制更新指定主题ID（测试用）")
    
    args = parser.parse_args()
    
    # 打印标题
    print_banner()
    
    # 检查配置文件
    if not os.path.exists(args.config):
        logger.warning(f"配置文件不存在: {args.config}")
        logger.info("将创建默认配置文件，请根据实际情况修改")
    
    # 根据模式执行对应功能
    try:
        if args.now:
            return run_immediate_update(args.config, args.days)
        elif args.schedule:
            return run_scheduler(args.config, args.hour, args.minute)
        elif args.stats:
            days = args.days or 7
            return show_statistics(args.config, days)
        elif args.test_api:
            return test_api_connection(args.config)
        elif args.dry_run:
            return dry_run(args.config, args.days)
        elif args.check_theme:
            return check_theme_end(args.config)
        elif args.theme_update:
            return run_theme_update(args.config, args.theme_id)
        elif args.list_themes:
            return list_themes(args.config)
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"程序执行异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())