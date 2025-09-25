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

def main():
    """主函数 - 每24小时执行一次"""
    
    logger.info("="*60)
    logger.info("微信公众号爬虫启动 - 24小时循环模式")
    logger.info("="*60)
    
    execution_count = 0
    interval_hours = 24
    interval_seconds = interval_hours * 3600
    
    while True:
        execution_count += 1
        
        # 显示执行信息
        logger.info(f"\n第 {execution_count} 次执行")
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
        
        # 计算下次执行时间
        next_run_time = datetime.now() + timedelta(hours=interval_hours)
        logger.info("="*60)
        logger.info(f"下次执行时间: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"等待 {interval_hours} 小时...")
        logger.info("="*60)
        
        # 等待24小时
        try:
            # 每小时显示一次剩余时间
            for hour in range(interval_hours):
                time.sleep(3600)  # 睡眠1小时
                remaining_hours = interval_hours - hour - 1
                if remaining_hours > 0:
                    logger.info(f"⏰ 距离下次执行还有 {remaining_hours} 小时")
        except KeyboardInterrupt:
            logger.warning("\n用户中断程序")
            logger.info(f"共执行了 {execution_count} 次爬虫任务")
            break

if __name__ == "__main__":
    main()