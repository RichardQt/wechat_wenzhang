#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号爬虫主程序
===================

提供统一的入口来执行爬虫任务
"""

import sys
import argparse
from spider.log.utils import logger

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='微信公众号文章爬虫')
    parser.add_argument('command', nargs='?', default='crawl',
                       choices=['crawl', 'test', 'login', 'db-test'],
                       help='执行的命令')
    parser.add_argument('--account', '-a', type=str,
                       help='指定要测试的公众号名称')
    parser.add_argument('--max-articles', '-m', type=int, default=50,
                       help='每个公众号最大爬取文章数')
    
    args = parser.parse_args()
    
    if args.command == 'crawl':
        # 执行完整爬取
        logger.info("开始执行完整爬取任务...")
        from wechat_crawler_auto import WeChatCrawlerAuto
        crawler = WeChatCrawlerAuto()
        crawler.run()
        
    elif args.command == 'test':
        # 测试爬取单个公众号
        if not args.account:
            logger.error("测试模式需要指定公众号名称，使用 --account 参数")
            sys.exit(1)
        
        logger.info(f"测试爬取公众号: {args.account}")
        from wechat_crawler_auto import WeChatCrawlerAuto
        crawler = WeChatCrawlerAuto()
        crawler.test_single_account(args.account)
        
    elif args.command == 'login':
        # 仅执行登录
        logger.info("执行登录测试...")
        from auto_login import test_auto_login
        test_auto_login()
        
    elif args.command == 'db-test':
        # 测试数据库连接
        logger.info("测试数据库连接...")
        from database import test_database
        test_database()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
