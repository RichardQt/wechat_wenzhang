#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号爬虫 - 24小时自动运行
================================

每24小时自动执行一次爬虫任务
"""

import time
from datetime import datetime, timedelta
from spider.log.utils import logger
from wechat_crawler_auto import WeChatCrawlerAuto

def get_next_run_time():
    """获取下次执行时间（每天凌晨1点）"""
    now = datetime.now()
    # 设置为今天凌晨1点
    next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)
    
    # 如果当前时间已经过了今天的凌晨1点，则设置为明天凌晨1点
    if next_run <= now:
        next_run += timedelta(days=1)
    
    return next_run

def main():
    """主函数 - 每24小时执行一次"""
    
    logger.info("="*60)
    logger.info("微信公众号爬虫启动 - 每日凌晨1点执行模式")
    logger.info("="*60)
    
    execution_count = 0
    
    while True:
        execution_count += 1
        
        # 记录开始时间
        start_time = datetime.now()
        
        # 显示执行信息
        logger.info(f"\n第 {execution_count} 次执行")
        logger.info(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        try:
            # 执行爬虫
            crawler = WeChatCrawlerAuto()
            crawler.run()
            logger.success("本次爬取完成")
        except KeyboardInterrupt:
            logger.warning("用户中断程序")
            break
        except Exception as e:
            logger.error(f"爬虫运行出错: {e}")
        
        # 计算下次执行时间（每天凌晨1点）
        next_run_time = get_next_run_time()
        logger.info("="*60)
        logger.info(f"下次执行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} (每日凌晨1点)")
        logger.info("="*60)
        
        # 计算等待时间
        wait_seconds = (next_run_time - datetime.now()).total_seconds()
        
        if wait_seconds > 0:
            # 等待到下次执行时间，每五小时显示一次剩余时间
            try:
                hours_to_wait = int(wait_seconds // 3600)
                logger.info(f"⏰ 需要等待 {hours_to_wait} 小时 {int((wait_seconds % 3600) // 60)} 分钟到凌晨1点")
                
                # 每5小时显示一次剩余时间
                elapsed_hours = 0
                while elapsed_hours < hours_to_wait:
                    sleep_duration = min(5 * 3600, (hours_to_wait - elapsed_hours) * 3600)  # 睡眠5小时或剩余时间
                    time.sleep(sleep_duration)
                    elapsed_hours += sleep_duration // 3600
                    
                    remaining_hours = hours_to_wait - elapsed_hours
                    if remaining_hours > 0:
                        logger.info(f"⏰ 距离凌晨1点执行还有 {remaining_hours} 小时")
                
                # 等待剩余秒数
                remaining_seconds = wait_seconds % 3600
                if remaining_seconds > 0:
                    time.sleep(remaining_seconds)
            except KeyboardInterrupt:
                logger.warning("\n用户中断程序")
                logger.info(f"共执行了 {execution_count} 次爬虫任务")
                break
        else:
            logger.warning("当前时间已过今日凌晨1点，立即开始执行")

if __name__ == "__main__":
    main()