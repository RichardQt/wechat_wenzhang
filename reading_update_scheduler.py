#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
阅读量更新定时任务
================

每天早上6点定时执行阅读量更新任务
"""

import time
import schedule
import threading
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from article_reading_updater import ArticleReadingUpdater
from spider.log.utils import logger


class ReadingUpdateScheduler:
    """阅读量更新定时调度器"""
    
    def __init__(self, config_file: str = "reading_updater_config.json"):
        """
        初始化调度器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.updater = ArticleReadingUpdater(config_file)
        self.running = False
        self.scheduler_thread = None
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _show_next_execution_time(self, hour: int, minute: int):
        """计算并显示下次执行时间"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        today_target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if now >= today_target:
            # 如果今天的时间已过，下次执行是明天
            next_execution = today_target + timedelta(days=1)
        else:
            # 如果今天的时间还没到，下次执行是今天
            next_execution = today_target
        
        logger.info(f"下次执行时间: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 计算等待时间
        wait_time = next_execution - now
        hours = wait_time.total_seconds() / 3600
        
        if hours < 24:
            logger.info(f"等待时间: {wait_time} ({hours:.1f} 小时)")
        else:
            days = int(hours / 24)
            remaining_hours = hours % 24
            logger.info(f"等待时间: {days} 天 {remaining_hours:.1f} 小时")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在停止调度器...")
        self.stop()
        sys.exit(0)
    
    def execute_update_task(self):
        """执行更新任务"""
        logger.info("="*60)
        logger.info("⏰ 定时任务触发 - 开始执行阅读量更新")
        logger.info("="*60)
        
        try:
            # 记录任务开始时间
            start_time = datetime.now()
            logger.info(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 执行更新任务
            success = self.updater.run_update()
            
            # 记录任务结束时间
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info(f"任务结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"执行耗时: {duration}")
            
            if success:
                logger.success("✅ 定时任务执行成功")
            else:
                logger.error("❌ 定时任务执行失败")
            
            # 获取统计信息
            stats = self.updater.get_update_statistics(7)
            if stats:
                logger.info(f"📊 当前状态: 近7天普法文章 {stats['updated_articles']}/{stats['total_articles']} "
                           f"已更新阅读量 (完成率: {stats['completion_rate']}%)")
            
        except Exception as e:
            logger.error(f"执行定时任务时发生异常: {e}")
        
        logger.info("="*60)
        logger.info("🏁 定时任务执行完成")
        logger.info("="*60)
        
        # 显示下次执行时间（任务执行后，下次一定是明天）
        try:
            import schedule
            from datetime import datetime as dt, timedelta
            now = dt.now()
            # 获取当前任务的执行时间配置
            jobs = schedule.get_jobs()
            if jobs:
                job = jobs[0]  # 应该只有一个任务
                # 从任务配置中获取时间
                job_time = job.at_time
                if job_time:
                    hour, minute = job_time.hour, job_time.minute
                    # 下次执行一定是明天的同一时间
                    tomorrow = now.date() + timedelta(days=1)
                    next_execution = dt.combine(tomorrow, job_time)
                    logger.info(f"⏰ 下次执行时间: {next_execution.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    wait_time = next_execution - now
                    hours = wait_time.total_seconds() / 3600
                    logger.info(f"⏱️ 距离下次执行: {hours:.1f} 小时")
                else:
                    logger.warning("⚠️ 无法获取任务执行时间配置")
            else:
                logger.warning("⚠️ 未找到已安排的任务")
        except Exception as e:
            logger.error(f"显示下次执行时间时出错: {e}")
    
    def schedule_daily_task(self, hour: int = 6, minute: int = 0):
        """
        安排每日定时任务
        
        Args:
            hour: 执行小时 (0-23)
            minute: 执行分钟 (0-59)
        """
        # 清除之前的任务
        schedule.clear()
        
        # 安排每日任务
        schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(self.execute_update_task)
        
        logger.info(f"已安排每日定时任务: 每天 {hour:02d}:{minute:02d} 执行阅读量更新")
        
        # 计算并显示下次执行时间
        self._show_next_execution_time(hour, minute)
    
    def run_scheduler(self):
        """运行调度器主循环"""
        logger.info("调度器开始运行...")
        
        while self.running:
            try:
                # 检查并执行待执行的任务
                schedule.run_pending()
                
                # 每分钟检查一次
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"调度器运行时发生异常: {e}")
                time.sleep(60)  # 出错时也要等待，避免循环过快
    
    def start(self, hour: int = 6, minute: int = 0):
        """
        启动定时调度器
        
        Args:
            hour: 执行小时 (0-23)
            minute: 执行分钟 (0-59)
        """
        if self.running:
            logger.warning("调度器已经在运行中")
            return
        
        logger.info("="*60)
        logger.info("🚀 阅读量更新定时调度器启动")
        logger.info("="*60)
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 安排定时任务
        self.schedule_daily_task(hour, minute)
        
        # 设置运行标志
        self.running = True
        
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.success("✅ 调度器启动成功")
        
        try:
            # 主线程保持运行
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到键盘中断信号")
            self.stop()
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        logger.info("正在停止调度器...")
        self.running = False
        
        # 清除所有任务
        schedule.clear()
        
        # 等待调度器线程结束
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("✅ 调度器已停止")
    
    def run_once(self):
        """立即执行一次更新任务"""
        logger.info("立即执行模式 - 开始执行阅读量更新任务")
        self.execute_update_task()
    
    def show_status(self):
        """显示调度器状态"""
        logger.info("="*50)
        logger.info("📊 调度器状态信息")
        logger.info("="*50)
        
        if self.running:
            logger.info("🟢 调度器状态: 运行中")
            
            # 显示下次执行时间
            next_run = schedule.next_run()
            if next_run:
                logger.info(f"⏰ 下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 显示所有已安排的任务
            jobs = schedule.get_jobs()
            if jobs:
                logger.info(f"📋 已安排任务数量: {len(jobs)}")
                for i, job in enumerate(jobs, 1):
                    logger.info(f"   {i}. {job}")
        else:
            logger.info("🔴 调度器状态: 未运行")
        
        # 显示统计信息
        stats = self.updater.get_update_statistics(7)
        if stats:
            logger.info("📈 近7天统计:")
            logger.info(f"   总文章数: {stats['total_articles']}")
            logger.info(f"   已更新数: {stats['updated_articles']}")
            logger.info(f"   待更新数: {stats['need_update_articles']}")
            logger.info(f"   完成率: {stats['completion_rate']}%")
        
        logger.info("="*50)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="阅读量更新定时调度器")
    parser.add_argument("--config", default="reading_updater_config.json", help="配置文件路径")
    parser.add_argument("--hour", type=int, default=6, help="执行小时 (0-23)")
    parser.add_argument("--minute", type=int, default=0, help="执行分钟 (0-59)")
    parser.add_argument("--now", action="store_true", help="立即执行一次任务")
    parser.add_argument("--status", action="store_true", help="显示调度器状态")
    parser.add_argument("--daemon", action="store_true", help="后台运行模式")
    
    args = parser.parse_args()
    
    # 创建调度器
    scheduler = ReadingUpdateScheduler(args.config)
    
    if args.status:
        # 显示状态信息
        scheduler.show_status()
    elif args.now:
        # 立即执行任务
        scheduler.run_once()
    else:
        # 启动定时调度器
        if args.daemon:
            logger.info("后台运行模式")
            # 在实际应用中，这里应该实现真正的守护进程
            # 目前只是模拟后台运行
        
        logger.info(f"将在每天 {args.hour:02d}:{args.minute:02d} 执行阅读量更新任务")
        scheduler.start(args.hour, args.minute)


if __name__ == "__main__":
    main()