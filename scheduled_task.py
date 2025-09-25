#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
微信公众号爬虫 - 定时任务
=======================

在指定时间执行一次爬虫任务
"""

import time
import subprocess
import os
from datetime import datetime, timedelta
from pathlib import Path
from spider.log.utils import logger

class ScheduledTask:
    """定时任务执行器"""
    
    def __init__(self):
        """初始化"""
        self.script_dir = Path(__file__).parent
        self.python_exe = self.script_dir / "venv" / "Scripts" / "python.exe"
        self.start_script = self.script_dir / "start.py"
        
    def wait_until_target_time(self, target_hour=0, target_minute=1):
        """等待到指定时间"""
        now = datetime.now()
        
        # 计算明天的目标时间
        tomorrow = now.date() + timedelta(days=1)
        target_time = datetime.combine(tomorrow, datetime.min.time())
        target_time = target_time.replace(hour=target_hour, minute=target_minute)
        
        # 计算等待时间
        wait_seconds = (target_time - now).total_seconds()
        
        logger.info("="*60)
        logger.info("微信公众号爬虫 - 定时任务启动")
        logger.info("="*60)
        logger.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"目标执行时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"等待时间: {wait_seconds:.0f} 秒 ({wait_seconds/3600:.1f} 小时)")
        logger.info("="*60)
        
        if wait_seconds <= 0:
            logger.warning("目标时间已过，将立即执行任务")
            return
        
        # 显示倒计时
        self._countdown(wait_seconds, target_time)
    
    def _countdown(self, total_seconds, target_time):
        """显示倒计时"""
        try:
            remaining = int(total_seconds)
            last_hour_logged = -1
            
            while remaining > 0:
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                
                # 每小时显示一次进度
                if hours != last_hour_logged and minutes == 0 and seconds <= 5:
                    if hours > 0:
                        logger.info(f"⏰ 距离执行还有 {hours} 小时")
                    last_hour_logged = hours
                
                # 最后5分钟每分钟显示一次
                if remaining <= 300 and seconds == 0:
                    logger.info(f"⏰ 距离执行还有 {minutes} 分 {seconds} 秒")
                
                # 最后30秒每秒显示一次
                if remaining <= 30:
                    logger.info(f"⏰ {remaining} 秒后执行任务...")
                
                time.sleep(1)
                remaining -= 1
                
        except KeyboardInterrupt:
            logger.warning("\n用户中断等待，程序退出")
            return False
        
        logger.success(f"⏰ 到达执行时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    
    def execute_crawler(self):
        """执行爬虫任务"""
        logger.info("="*60)
        logger.info("开始执行微信公众号爬虫任务")
        logger.info("="*60)
        
        try:
            # 检查文件是否存在
            if not self.python_exe.exists():
                logger.error(f"Python解释器不存在: {self.python_exe}")
                return False
                
            if not self.start_script.exists():
                logger.error(f"启动脚本不存在: {self.start_script}")
                return False
            
            # 切换到脚本目录
            os.chdir(self.script_dir)
            logger.info(f"工作目录: {self.script_dir}")
            logger.info(f"Python解释器: {self.python_exe}")
            logger.info(f"执行脚本: {self.start_script}")
            
            # 执行命令
            cmd = [str(self.python_exe), str(self.start_script)]
            logger.info(f"执行命令: {' '.join(cmd)}")
            
            start_time = datetime.now()
            logger.info(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 执行子进程，不捕获输出，让其直接显示在控制台
            # 这将允许您实时看到 start.py 的日志
            result = subprocess.run(
                cmd,
                cwd=self.script_dir
                # 移除了 capture_output=True，这是关键
            )
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"任务结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"执行耗时: {duration}")
            
            # 显示执行结果
            if result.returncode == 0:
                logger.success("✅ 爬虫任务执行成功")
            else:
                logger.error(f"❌ 爬虫任务执行失败，退出码: {result.returncode}")
                logger.error("请检查上面的日志输出以了解详细错误信息。")
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"执行爬虫任务时发生异常: {e}")
            return False
    
    def run(self, target_hour=0, target_minute=1):
        """运行定时任务"""
        try:
            # 等待到目标时间
            if self.wait_until_target_time(target_hour, target_minute) is False:
                return
            
            # 执行爬虫任务
            success = self.execute_crawler()
            
            if success:
                logger.success("="*60)
                logger.success("🎉 定时任务执行完成！")
                logger.success("="*60)
            else:
                logger.error("="*60)
                logger.error("❌ 定时任务执行失败！")
                logger.error("="*60)
                
        except KeyboardInterrupt:
            logger.warning("\n用户中断程序")
        except Exception as e:
            logger.error(f"定时任务运行出错: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="微信公众号爬虫定时任务")
    parser.add_argument("--hour", type=int, default=0, help="执行小时 (0-23)")
    parser.add_argument("--minute", type=int, default=1, help="执行分钟 (0-59)")
    parser.add_argument("--now", action="store_true", help="立即执行任务")
    
    args = parser.parse_args()
    
    task = ScheduledTask()
    
    if args.now:
        logger.info("立即执行模式")
        task.execute_crawler()
    else:
        task.run(args.hour, args.minute)

if __name__ == "__main__":
    main()