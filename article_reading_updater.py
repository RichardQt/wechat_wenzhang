#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文章阅读量更新器
===============

定时扫描近7天普法文章，调用第三方API获取阅读量并更新数据库
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database import DatabaseManager
from dsf_api_client import DSFApiClient
from spider.log.utils import logger


class ArticleReadingUpdater:
    """文章阅读量更新器"""
    
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
        self.days_to_check = self.config.get('days_to_check', 7)  # 检查近7天
        self.batch_size = self.config.get('batch_size', 50)       # 批处理大小
        self.max_retries = self.config.get('max_retries', 3)      # 最大重试次数
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"配置文件加载成功: {self.config_file}")
                return config
        except FileNotFoundError:
            logger.warning(f"配置文件不存在，使用默认配置: {self.config_file}")
            default_config = self._get_default_config()
            self._save_config(default_config)
            return default_config
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
            "days_to_check": 7,
            "batch_size": 50,
            "max_retries": 3,
            "enabled": True
        }
    
    def _save_config(self, config: Dict):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                logger.info(f"配置文件保存成功: {self.config_file}")
        except Exception as e:
            logger.error(f"配置文件保存失败: {e}")
    
    def get_articles_need_update(self, days: int = None, only_empty: bool = False) -> List[Dict]:
        """
        获取需要更新阅读量的普法文章
        
        Args:
            days: 检查的天数，默认使用配置值
            only_empty: 是否只获取阅读量为空的文章
            
        Returns:
            List[Dict]: 需要更新的文章列表
        """
        if days is None:
            days = self.days_to_check
        
        # 确保数据库已连接
        if not self.db.connection:
            logger.error("数据库未连接，无法查询文章")
            return []
            
        try:
            with self.db.connection.cursor() as cursor:
                # 计算时间范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # 基础查询条件：
                # 1. 是普法文章 (fx_education_articles.type_class = '1')
                # 2. 在指定时间范围内
                # 3. 有有效的文章URL
                base_conditions = """
                WHERE ea.type_class = '1'
                  AND ar.publish_time >= %s
                  AND ar.publish_time <= %s
                  AND ar.article_url IS NOT NULL 
                  AND ar.article_url != ''
                """
                
                # 如果只获取阅读量为空的文章，添加额外条件
                if only_empty:
                    base_conditions += """
                  AND (ar.view_count IS NULL 
                       OR ar.likes IS NULL 
                       OR ar.thumbs_count IS NULL)
                    """
                
                sql = f"""
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
                {base_conditions}
                ORDER BY ar.publish_time DESC
                """
                
                cursor.execute(sql, (start_date, end_date))
                articles = cursor.fetchall()
                
                article_type = "阅读量为空的" if only_empty else ""
                logger.info(f"查询到 {len(articles)} 篇需要更新{article_type}普法文章 "
                           f"(时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')})")
                
                return articles
                
        except Exception as e:
            logger.error(f"查询需要更新的文章时出错: {e}")
            return []
    
    def get_articles_for_specific_day(self, target_date: datetime) -> List[Dict]:
        """
        获取指定日期发布的普法文章
        
        Args:
            target_date: 目标日期
            
        Returns:
            List[Dict]: 该日期发布的文章列表
        """
        # 确保数据库已连接
        if not self.db.connection:
            logger.error("数据库未连接，无法查询文章")
            return []
            
        try:
            with self.db.connection.cursor() as cursor:
                # 计算当天的开始和结束时间
                day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # 查询条件：
                # 1. 是普法文章 (fx_education_articles.type_class = '1')
                # 2. 发布时间在目标日期当天
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
                
                logger.info(f"查询到 {len(articles)} 篇需要更新的普法文章 "
                           f"(发布日期: {target_date.strftime('%Y-%m-%d')})")
                
                return articles
                
        except Exception as e:
            logger.error(f"查询指定日期文章时出错: {e}")
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
                    stats['read'],      # 阅读量 -> view_count
                    stats['looking'],   # 在看量 -> likes
                    stats['zan'],       # 点赞量 -> thumbs_count
                    current_time,       # 更新时间
                    article_id          # 文章ID
                )
                
                cursor.execute(sql, values)
                self.db.connection.commit()
                
                logger.success(f"文章数据更新成功: {article_title[:50]} - "
                             f"阅读:{stats['read']} 在看:{stats['looking']} 点赞:{stats['zan']}")
                
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
                
                # 更新文章数据
                if self.update_article_reading_data(article):
                    success_count += 1
                
                # 进度提示
                if i % 10 == 0:
                    logger.info(f"已处理 {i}/{total_count} 篇，成功 {success_count} 篇")
                
            except Exception as e:
                logger.error(f"处理第 {i} 篇文章时出错: {e}")
                continue
        
        logger.info(f"批量更新完成: 成功 {success_count}/{total_count} 篇")
        return success_count, total_count
    
    def run_update(self) -> bool:
        """
        执行更新任务
        
        Returns:
            bool: 任务执行成功返回True
        """
        try:
            # 检查配置
            if not self.config.get('enabled', True):
                logger.info("更新任务已禁用，跳过执行")
                return True
            
            if not self.config.get('api', {}).get('key'):
                logger.error("API密钥未配置，无法执行更新任务")
                return False
            
            # 连接数据库
            if not self.db.connect():
                logger.error("数据库连接失败")
                return False
            
            start_time = datetime.now()
            logger.info("="*60)
            logger.info("🚀 开始执行文章阅读量更新任务")
            logger.info("="*60)
            logger.info(f"任务开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"检查范围: 近 {self.days_to_check} 天的普法文章")
            
            # 第一步：获取近7天内阅读量为空的文章（只填充）
            logger.info("\n" + "="*60)
            logger.info("📝 第一步：填充近7天内阅读量为空的文章")
            logger.info("="*60)
            empty_articles = self.get_articles_need_update(only_empty=True)
            
            # 第二步：获取往前推6天那一天的所有文章（强制更新）
            six_days_ago = datetime.now() - timedelta(days=6)
            logger.info("\n" + "="*60)
            logger.info(f"📅 第二步：更新往前推6天的文章 (发布日期: {six_days_ago.strftime('%Y-%m-%d')})")
            logger.info("="*60)
            six_days_ago_articles = self.get_articles_for_specific_day(six_days_ago)
            
            # 合并文章列表，去重（基于article_id）
            all_articles = empty_articles.copy() if empty_articles else []
            existing_article_ids = {article['article_id'] for article in all_articles}
            
            # 添加前6天的文章（去重）
            additional_count = 0
            for article in six_days_ago_articles:
                if article['article_id'] not in existing_article_ids:
                    all_articles.append(article)
                    existing_article_ids.add(article['article_id'])
                    additional_count += 1
            
            if not all_articles:
                logger.info("没有需要处理的文章，任务完成")
                return True
            
            logger.info("\n" + "="*60)
            logger.info("📊 任务汇总")
            logger.info("="*60)
            logger.info(f"近{self.days_to_check}天阅读量为空的文章(填充): {len(empty_articles)} 篇")
            logger.info(f"往前推6天({six_days_ago.strftime('%Y-%m-%d')})的文章(更新): {len(six_days_ago_articles)} 篇")
            logger.info(f"去重后实际需要处理: {len(all_articles)} 篇")
            logger.info(f"  - 其中需要填充: {len(empty_articles)} 篇")
            logger.info(f"  - 其中需要更新: {additional_count} 篇")
            logger.info("")
            
            # 批量更新
            success_count, total_count = self.batch_update_articles(all_articles)
            
            # 统计结果
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("="*60)
            logger.info("📊 任务执行完成")
            logger.info("="*60)
            logger.info(f"任务结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"执行耗时: {duration}")
            logger.info(f"处理结果: 成功 {success_count}/{total_count} 篇")
            
            if success_count > 0:
                logger.success(f"✅ 成功处理了 {success_count} 篇文章的阅读量数据")
            
            if success_count < total_count:
                failed_count = total_count - success_count
                logger.warning(f"⚠️  有 {failed_count} 篇文章处理失败")
            
            return True
            
        except Exception as e:
            logger.error(f"执行更新任务时发生异常: {e}")
            return False
            
        finally:
            # 关闭数据库连接
            self.db.disconnect()
    
    def get_update_statistics(self, days: int = 7) -> Dict:
        """
        获取更新统计信息
        
        Args:
            days: 统计的天数
            
        Returns:
            Dict: 统计信息
        """
        try:
            if not self.db.connect():
                return {}
            
            with self.db.connection.cursor() as cursor:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # 统计普法文章总数
                sql_total = """
                SELECT COUNT(*) as total_count
                FROM fx_article_records ar
                INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
                WHERE ea.type_class = '1'
                  AND ar.publish_time >= %s
                  AND ar.publish_time <= %s
                """
                cursor.execute(sql_total, (start_date, end_date))
                total_result = cursor.fetchone()
                total_count = total_result['total_count'] if total_result else 0
                
                # 统计已有阅读量数据的文章数
                sql_updated = """
                SELECT COUNT(*) as updated_count
                FROM fx_article_records ar
                INNER JOIN fx_education_articles ea ON ar.article_id = ea.article_id
                WHERE ea.type_class = '1'
                  AND ar.publish_time >= %s
                  AND ar.publish_time <= %s
                  AND ar.view_count IS NOT NULL
                  AND ar.likes IS NOT NULL
                  AND ar.thumbs_count IS NOT NULL
                """
                cursor.execute(sql_updated, (start_date, end_date))
                updated_result = cursor.fetchone()
                updated_count = updated_result['updated_count'] if updated_result else 0
                
                # 计算需要更新的数量
                need_update_count = total_count - updated_count
                completion_rate = (updated_count / total_count * 100) if total_count > 0 else 0
                
                stats = {
                    'total_articles': total_count,
                    'updated_articles': updated_count,
                    'need_update_articles': need_update_count,
                    'completion_rate': round(completion_rate, 2),
                    'date_range': {
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d')
                    }
                }
                
                logger.info(f"统计信息 ({days}天): 总数{total_count} 已更新{updated_count} "
                           f"待更新{need_update_count} 完成率{completion_rate:.1f}%")
                
                return stats
                
        except Exception as e:
            logger.error(f"获取统计信息时出错: {e}")
            return {}
        finally:
            self.db.disconnect()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="文章阅读量更新器")
    parser.add_argument("--config", default="reading_updater_config.json", help="配置文件路径")
    parser.add_argument("--days", type=int, help="检查的天数")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式（只查询不更新）")
    
    args = parser.parse_args()
    
    # 创建更新器
    updater = ArticleReadingUpdater(args.config)
    
    if args.stats:
        # 显示统计信息
        days = args.days or 7
        stats = updater.get_update_statistics(days)
        if stats:
            print(f"\n📊 近{days}天普法文章阅读量统计:")
            print(f"总文章数: {stats['total_articles']}")
            print(f"已更新数: {stats['updated_articles']}")
            print(f"待更新数: {stats['need_update_articles']}")
            print(f"完成率: {stats['completion_rate']}%")
            print(f"时间范围: {stats['date_range']['start_date']} 到 {stats['date_range']['end_date']}")
    elif args.dry_run:
        # 试运行模式
        if not updater.db.connect():
            logger.error("数据库连接失败")
            return
        
        articles = updater.get_articles_need_update(args.days)
        logger.info(f"试运行模式: 找到 {len(articles)} 篇需要更新的文章")
        
        for i, article in enumerate(articles[:5], 1):  # 只显示前5篇
            logger.info(f"{i}. {article['article_title'][:50]} (发布时间: {article['publish_time']})")
        
        if len(articles) > 5:
            logger.info(f"... 还有 {len(articles) - 5} 篇文章")
            
        updater.db.disconnect()
    else:
        # 执行更新任务
        success = updater.run_update()
        if success:
            logger.success("更新任务执行成功")
        else:
            logger.error("更新任务执行失败")


if __name__ == "__main__":
    main()