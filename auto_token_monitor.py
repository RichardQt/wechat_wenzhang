#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信Token自动监控脚本

这个脚本用于自动检测微信公众号Token的过期状态，并在需要时发送提醒邮件。
具有防重复提醒机制，确保同类型的提醒只发送一次。

主要特性：
- 自动检测Token过期状态
- 防重复提醒机制
- 详细的日志记录
- 支持静默模式运行
- 适合定时任务调用

使用方法：
1. 直接运行：python auto_token_monitor.py
2. 静默模式：python auto_token_monitor.py --quiet
3. 强制检查：python auto_token_monitor.py --force

作者: Kilo Code
创建时间: 2024
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# 确保可以导入notify模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from notify import auto_check_and_notify, check_token_expiry, send_token_expiry_notification
except ImportError as e:
    print(f"导入notify模块失败: {e}")
    print("请确保notify.py文件存在于同一目录中")
    sys.exit(1)


def setup_logging(quiet=False, log_file='auto_token_monitor.log'):
    """配置日志系统
    
    Args:
        quiet (bool): 是否启用静默模式
        log_file (str): 日志文件路径
    """
    # 配置日志格式
    log_format = '%(asctime)s - [AUTO_MONITOR] - %(levelname)s - %(message)s'
    
    # 创建日志处理器列表
    handlers = [logging.FileHandler(log_file, encoding='utf-8')]
    
    # 如果不是静默模式，添加控制台输出
    if not quiet:
        handlers.append(logging.StreamHandler())
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers,
        force=True  # 强制重新配置，覆盖notify.py中的配置
    )


def run_auto_check(force=False, quiet=False):
    """运行自动检测
    
    Args:
        force (bool): 是否强制发送提醒（忽略防重复机制）
        quiet (bool): 是否启用静默模式
    
    Returns:
        dict: 检测结果
    """
    try:
        logging.info("=" * 60)
        logging.info("开始执行Token自动监控检查")
        logging.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"运行模式: {'强制模式' if force else '自动模式'}")
        logging.info("=" * 60)
        
        if force:
            # 强制模式：忽略防重复机制，直接检查并发送提醒
            logging.info("强制模式：忽略提醒历史，强制检查并发送提醒")
            
            is_expiring, hours_remaining, expiry_time, reminder_type = check_token_expiry()
            
            result = {
                'check_successful': True,
                'reminder_needed': is_expiring,
                'reminder_sent': False,
                'reminder_type': reminder_type,
                'message': '',
                'hours_remaining': hours_remaining,
                'mode': 'force'
            }
            
            if is_expiring and hours_remaining is not None and expiry_time is not None and reminder_type is not None:
                # 发送强制提醒
                success = send_token_expiry_notification(hours_remaining, expiry_time, reminder_type)
                result['reminder_sent'] = success
                
                if success:
                    if reminder_type == 'expired':
                        result['message'] = "Token已过期，强制提醒邮件已发送"
                    else:
                        result['message'] = f"Token即将过期（剩余{hours_remaining:.1f}小时），强制提醒邮件已发送"
                    logging.info(result['message'])
                else:
                    result['message'] = "强制提醒邮件发送失败"
                    logging.error(result['message'])
            elif not is_expiring and hours_remaining is not None:
                days_remaining = hours_remaining / 24
                result['message'] = f"Token状态正常，剩余有效期：{days_remaining:.1f}天"
                logging.info(result['message'])
            else:
                result['message'] = "无法获取Token状态信息"
                result['check_successful'] = False
                logging.error(result['message'])
            
        else:
            # 自动模式：使用防重复提醒机制
            logging.info("自动模式：使用防重复提醒机制")
            result = auto_check_and_notify()
            result['mode'] = 'auto'
        
        # 记录检查结果摘要
        logging.info("-" * 40)
        logging.info("检查结果摘要:")
        logging.info(f"✅ 检查成功: {result['check_successful']}")
        logging.info(f"⚠️  需要提醒: {result['reminder_needed']}")
        logging.info(f"📧 邮件已发送: {result['reminder_sent']}")
        if result['reminder_type']:
            logging.info(f"🏷️  提醒类型: {result['reminder_type']}")
        if result['hours_remaining'] is not None:
            logging.info(f"⏰ 剩余时间: {result['hours_remaining']:.1f}小时")
        logging.info(f"💬 详细信息: {result['message']}")
        logging.info("-" * 40)
        
        return result
        
    except Exception as e:
        error_msg = f"自动监控检查过程中发生未预期的错误: {str(e)}"
        logging.error(error_msg)
        
        return {
            'check_successful': False,
            'reminder_needed': False,
            'reminder_sent': False,
            'reminder_type': None,
            'message': error_msg,
            'hours_remaining': None,
            'mode': 'error'
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='微信Token自动监控工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                    # 正常自动检测（防重复提醒）
  %(prog)s --quiet            # 静默模式运行
  %(prog)s --force            # 强制发送提醒（忽略历史记录）
  %(prog)s --force --quiet    # 静默强制模式

注意事项:
  - 自动模式会使用防重复提醒机制，同类型提醒只发送一次
  - 强制模式会忽略提醒历史，每次都发送提醒
  - 静默模式只会将日志写入文件，不会在控制台输出
  - 适合配置定时任务，建议每2-4小时运行一次
        """
    )
    
    parser.add_argument('--force', action='store_true',
                       help='强制模式：忽略提醒历史，强制检查并发送提醒')
    parser.add_argument('--quiet', action='store_true',
                       help='静默模式：只记录日志文件，不输出到控制台')
    parser.add_argument('--log-file', default='auto_token_monitor.log',
                       help='指定日志文件路径（默认：auto_token_monitor.log）')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(quiet=args.quiet, log_file=args.log_file)
    
    # 运行自动检测
    result = run_auto_check(force=args.force, quiet=args.quiet)
    
    # 确定退出代码
    if result['check_successful']:
        if result['reminder_needed'] and not result['reminder_sent']:
            # 需要提醒但未发送（通常是防重复机制）
            exit_code = 0  # 正常，因为这是预期行为
        else:
            exit_code = 0  # 正常完成
    else:
        exit_code = 1  # 检查失败
    
    if not args.quiet:
        print("\n" + "=" * 60)
        print("Token自动监控检查完成")
        if exit_code == 0:
            print("✅ 状态：正常")
        else:
            print("❌ 状态：异常")
        print(f"详细日志已记录到：{args.log_file}")
        print("=" * 60)
    
    logging.info(f"Token自动监控检查完成，退出代码: {exit_code}")
    logging.info("=" * 60 + "\n")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()