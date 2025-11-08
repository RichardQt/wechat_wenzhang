#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
法律主题月阅读量更新器
===================

在法律主题日结束前一天，更新该主题期间(start_date到end_date)的普法文章阅读量
"""

import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database import DatabaseManager
from dsf_api_client import DSFApiClient
from spider.log.utils import logger


class ThemeReadingUpdater:
    """法律主题月阅读量更新器"""
    
    def __init__(self, config_file: str = "reading_updater_config.json"):
        """
        初始化更新器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config()
        
        # 初始化数据库管理器
        self.db = DatabaseManager(
            host=self.config.get('database', {}).get('host', '127.0.0.1'),
            port=self.config.get('database', {}).get('port', 3306),
            user=self.config.get('database', {}).get('user', 'root'),
            password=self.config.get('database', {}).get('password', '123456'),
            database=self.config.get('database', {}).get('database', 'faxuan')
        )
        
        # 初始化API客户端
        api_config = self.config.get('api', {})
        self.api_client = DSFApiClient(
            api_key=api_config.get('key', ''),
            verify_code=api_config.get('verify_code', ''),
            base_url=api_config.get('base_url', 'https://www.dajiala.com')
        )
        
        # 配置参数
        self.batch_size = self.config.get('batch_size', 50)
        self.max_retries = self.config.get('max_retries', 3)
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"配置文件加载成功: {self.config_file}")
                return config
        except FileNotFoundError:
            logger.warning(f"配置文件不存在，使用默认配置: {self.config_file}")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "database": {
                "host": "127.0.0.1",
                "port": 3306,
                "user": "root",
                "password": "123456",
                "database": "faxuan"
            },
            "api": {
                "key": "your_api_key_here",
                "verify_code": "",
                "base_url": "https://www.dajiala.com"
            },
            "batch_size": 50,
            "max_retries": 3,
            "enabled": True
        }
    
    def get_upcoming_theme_end(self, check_date: datetime = None) -> Optional[Dict]:
        """
        检查指定日期的明天是否是某个法律主题月的结束日期
        
        Args:
            check_date: 检查日期，默认为今天
            
        Returns:
            Optional[Dict]: 如果明天是主题结束日，返回主题信息，否则返回None
        """
        if check_date is None:
            check_date = datetime.now()
        
        # 计算明天的日期
        tomorrow = check_date.date() + timedelta(days=1)
        
        # 确保数据库已连接
        if not self.db.connection:
            logger.error("数据库未连接，无法查询主题")
            return None
        
        try:
            with self.db.connection.cursor() as cursor:
                # 查询明天是否是某个主题的结束日期
                # 条件：status=1(使用中) AND end_date=明天
                sql = """
                SELECT 
                    id,
                    year,
                    theme_name,
                    start_date,
                    end_date,
                    `generate` as is_generated
                FROM fx_theme
                WHERE status = 1
                  AND end_date = %s
                LIMIT 1
                """
                
                cursor.execute(sql, (tomorrow,))
                theme = cursor.fetchone()
                
                if theme:
                    logger.info(f"检测到即将结束的法律主题: {theme['theme_name']} "
                               f"(结束日期: {theme['end_date']}, 明天是最后一天)")
                    logger.info(f"主题时间范围: {theme['start_date']} 到 {theme['end_date']}")
                    return theme
                else:
                    logger.info(f"明天 ({tomorrow}) 不是任何法律主题的结束日期")
                    return None
                    
        except Exception as e:
            logger.error(f"查询法律主题时出错: {e}")
            return None
    
    def get_articles_in_theme_period(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        获取法律主题期间发布的普法文章
        
        Args:
            start_date: 主题开始日期
            end_date: 主题结束日期
            
        Returns:
            List[Dict]: 该期间发布的普法文章列表
        """
        # 确保数据库已连接
        if not self.db.connection:
            logger.error("数据库未连接，无法查询文章")
            return []
        
        try:
            with self.db.connection.cursor() as cursor:
                # 转换日期为datetime类型（包含整天）
                day_start = datetime.combine(start_date, datetime.min.time())
                day_end = datetime.combine(end_date, datetime.max.time())
                
                # 查询条件：
                # 1. 是普法文章 (fx_education_articles.type_class = '1')
                # 2. 发布时间在主题期间内
                # 3. 有有效的文章URL
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
                
                cursor.execute(sql, (day_start, day_end))
                articles = cursor.fetchall()
                
                logger.info(f"查询到 {len(articles)} 篇主题期间的普法文章 "
                           f"(时间范围: {start_date} 到 {end_date})")
                
                return articles
                
        except Exception as e:
            logger.error(f"查询主题期间文章时出错: {e}")
            return []
    
    def update_article_reading_data(self, article: Dict) -> bool:
        """
        更新单篇文章的阅读量数据
        
        Args:
            article: 文章信息字典
            
        Returns:
            bool: 更新成功返回True
        """
        try:
            article_url = article['article_url']
            article_id = article['article_id']
            article_title = article.get('article_title', '无标题')
            
            logger.info(f"更新文章阅读数据: {article_title[:50]}...")
            
            # 调用API获取数据
            success, stats, error = self.api_client.get_article_stats(article_url)
            
            if not success:
                logger.warning(f"获取文章数据失败: {error}")
                return False
            
            # 更新数据库
            with self.db.connection.cursor() as cursor:
                sql = """
                UPDATE fx_article_records 
                SET view_count = %s,
                    likes = %s,
                    thumbs_count = %s,
                    update_time = %s
                WHERE article_id = %s
                """
                
                current_time = datetime.now()
                values = (
                    stats['read'],
                    stats['zan'],
                    stats['looking'],
                    current_time,
                    article_id
                )
                
                cursor.execute(sql, values)
                self.db.connection.commit()
                
                logger.success(f"文章数据已更新: 阅读{stats['read']} 点赞{stats['zan']} 在看{stats['looking']}")
                return True
                
        except Exception as e:
            logger.error(f"更新文章数据时出错: {e}")
            if self.db.connection:
                self.db.connection.rollback()
            return False
    
    def batch_update_articles(self, articles: List[Dict]) -> Tuple[int, int]:
        """
        批量更新文章阅读量数据
        
        Args:
            articles: 文章列表
            
        Returns:
            Tuple[int, int]: (成功数量, 总数量)
        """
        if not articles:
            logger.info("没有需要更新的文章")
            return 0, 0
        
        total_count = len(articles)
        success_count = 0
        
        logger.info(f"开始批量更新 {total_count} 篇文章的阅读量...")
        
        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"处理进度: {i}/{total_count}")
                
                if self.update_article_reading_data(article):
                    success_count += 1
                
                # 避免请求过快，每次请求后暂停
                import time
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"处理第 {i} 篇文章时出错: {e}")
                continue
        
        logger.info(f"批量更新完成: 成功 {success_count}/{total_count} 篇")
        return success_count, total_count
    
    def run_theme_update(self, force_theme_id: int = None) -> bool:
        """
        执行法律主题月阅读量更新任务
        
        Args:
            force_theme_id: 强制指定主题ID（用于测试）
            
        Returns:
            bool: 任务执行成功返回True
        """
        try:
            # 检查配置
            if not self.config.get('enabled', True):
                logger.warning("阅读量更新功能已禁用")
                return False
            
            if not self.config.get('api', {}).get('key'):
                logger.error("API密钥未配置")
                return False
            
            # 连接数据库
            if not self.db.connect():
                logger.error("数据库连接失败")
                return False
            
            start_time = datetime.now()
            logger.info("="*60)
            logger.info("🎯 开始执行法律主题月阅读量更新任务")
            logger.info("="*60)
            logger.info(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 获取即将结束的主题
            theme = None
            if force_theme_id:
                # 强制指定主题（测试模式）
                logger.info(f"测试模式：强制使用主题ID {force_theme_id}")
                with self.db.connection.cursor() as cursor:
                    sql = "SELECT id, year, theme_name, start_date, end_date, `generate` as is_generated FROM fx_theme WHERE id = %s"
                    cursor.execute(sql, (force_theme_id,))
                    theme = cursor.fetchone()
            else:
                # 正常模式：检查明天是否是主题结束日
                theme = self.get_upcoming_theme_end()
            
            if not theme:
                logger.info("当前没有需要更新的法律主题")
                return True
            
            logger.info(f"目标主题: {theme['theme_name']} (ID: {theme['id']})")
            logger.info(f"主题年份: {theme['year']}")
            logger.info(f"主题时间范围: {theme['start_date']} 到 {theme['end_date']}")
            
            # 获取主题期间的普法文章
            articles = self.get_articles_in_theme_period(
                theme['start_date'], 
                theme['end_date']
            )
            
            if not articles:
                logger.info(f"主题期间没有普法文章需要更新")
                return True
            
            logger.info(f"找到 {len(articles)} 篇主题期间的普法文章")
            
            # 批量更新文章阅读量
            success_count, total_count = self.batch_update_articles(articles)
            
            # 统计结果
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("="*60)
            logger.info("📊 任务执行完成")
            logger.info("="*60)
            logger.info(f"主题名称: {theme['theme_name']}")
            logger.info(f"主题时间: {theme['start_date']} 到 {theme['end_date']}")
            logger.info(f"任务结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"执行耗时: {duration}")
            logger.info(f"处理结果: 成功 {success_count}/{total_count} 篇")
            
            if success_count > 0:
                logger.success(f"✅ 成功更新 {success_count} 篇文章的阅读量")
            
            if success_count < total_count:
                logger.warning(f"⚠️ 有 {total_count - success_count} 篇文章更新失败")
            
            return True
            
        except Exception as e:
            logger.error(f"执行法律主题更新任务时发生异常: {e}")
            return False
            
        finally:
            # 关闭数据库连接
            self.db.disconnect()
    
    def list_active_themes(self) -> List[Dict]:
        """
        列出所有活动中的法律主题
        
        Returns:
            List[Dict]: 活动主题列表
        """
        if not self.db.connect():
            logger.error("数据库连接失败")
            return []
        
        try:
            with self.db.connection.cursor() as cursor:
                sql = """
                SELECT 
                    id,
                    year,
                    theme_name,
                    start_date,
                    end_date,
                    `generate` as is_generated,
                    modifier,
                    modify_time
                FROM fx_theme
                WHERE status = 1
                ORDER BY end_date DESC
                """
                
                cursor.execute(sql)
                themes = cursor.fetchall()
                
                return themes
                
        except Exception as e:
            logger.error(f"查询活动主题时出错: {e}")
            return []
        finally:
            self.db.disconnect()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="法律主题月阅读量更新器")
    parser.add_argument("--config", default="reading_updater_config.json", help="配置文件路径")
    parser.add_argument("--check", action="store_true", help="检查明天是否有主题结束")
    parser.add_argument("--list", action="store_true", help="列出所有活动主题")
    parser.add_argument("--theme-id", type=int, help="强制更新指定主题ID的文章（测试用）")
    parser.add_argument("--run", action="store_true", help="执行更新任务")
    
    args = parser.parse_args()
    
    # 创建更新器
    updater = ThemeReadingUpdater(args.config)
    
    if args.list:
        # 列出所有活动主题
        themes = updater.list_active_themes()
        if themes:
            print("\n📋 活动中的法律主题:")
            print("="*80)
            for theme in themes:
                print(f"ID: {theme['id']:3d} | {theme['theme_name']:<30s} | "
                      f"{theme['start_date']} ~ {theme['end_date']} | "
                      f"已生成: {'是' if theme['is_generated'] else '否'}")
            print("="*80)
        else:
            print("没有找到活动主题")
    
    elif args.check:
        # 检查明天是否有主题结束
        if not updater.db.connect():
            logger.error("数据库连接失败")
            return
        
        theme = updater.get_upcoming_theme_end()
        if theme:
            print(f"\n✅ 明天是法律主题结束日:")
            print(f"主题名称: {theme['theme_name']}")
            print(f"时间范围: {theme['start_date']} 到 {theme['end_date']}")
            print(f"主题ID: {theme['id']}")
        else:
            print("\n❌ 明天不是任何法律主题的结束日")
        
        updater.db.disconnect()
    
    elif args.run or args.theme_id:
        # 执行更新任务
        success = updater.run_theme_update(force_theme_id=args.theme_id)
        if success:
            logger.success("✅ 法律主题更新任务执行成功")
        else:
            logger.error("❌ 法律主题更新任务执行失败")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
