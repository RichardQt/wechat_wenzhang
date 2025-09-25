#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库管理模块
=============

处理MySQL数据库连接和文章数据存储
"""

import pymysql
import json
import random
from datetime import datetime
from spider.log.utils import logger
from typing import Dict, List, Optional

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, host='127.0.0.1', port=3306, user='root', password='123456', database='faxuan'):
        """
        初始化数据库管理器
        
        Args:
            host: 数据库主机地址
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名称
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.unit_mapping = {}  # 公众号名称到单位名称的映射
        
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.success(f"成功连接到数据库 {self.database}")
            # 加载单位名称映射
            self.load_unit_mapping()
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def load_unit_mapping(self):
        """从数据库加载公众号到单位名称的映射"""
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT unit_name, gzh_name FROM fx_unit_gzh_contrast WHERE gzh_name IS NOT NULL AND gzh_name != '无'"
                cursor.execute(sql)
                results = cursor.fetchall()
                
                # 构建映射字典：公众号名称 -> 单位名称
                self.unit_mapping = {}
                for row in results:
                    gzh_name = row['gzh_name']
                    unit_name = row['unit_name']
                    if gzh_name and unit_name:
                        self.unit_mapping[gzh_name] = unit_name
                
                logger.info(f"加载了 {len(self.unit_mapping)} 个单位名称映射")
                logger.debug(f"单位映射: {self.unit_mapping}")
        except Exception as e:
            logger.error(f"加载单位名称映射时出错: {e}")
            self.unit_mapping = {}
    
    def get_unit_name(self, gzh_name: str) -> str:
        """
        根据公众号名称获取对应的单位名称
        
        Args:
            gzh_name: 公众号名称
            
        Returns:
            str: 对应的单位名称，如果没有映射则返回原公众号名称
        """
        return self.unit_mapping.get(gzh_name, gzh_name)
    
    def disconnect(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")
    
    def generate_article_id(self, publish_time: datetime) -> str:
        """
        生成文章ID
        格式：发布时间(YYYYMMDDHHmmss) + 4位随机数
        
        Args:
            publish_time: 文章发布时间
            
        Returns:
            str: 生成的文章ID
        """
        time_str = publish_time.strftime("%Y%m%d%H%M%S")
        random_suffix = str(random.randint(1000, 9999))
        return f"{time_str}{random_suffix}"
    
    def check_article_exists(self, article_url: str) -> bool:
        """
        检查文章是否已存在（通过URL）
        
        Args:
            article_url: 文章URL
            
        Returns:
            bool: 如果文章存在返回True，否则返回False
        """
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT id FROM fx_article_records WHERE article_url = %s LIMIT 1"
                cursor.execute(sql, (article_url,))
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"检查文章URL是否存在时出错: {e}")
            return False
    
    def check_article_exists_by_title(self, title: str, unit_name: str) -> bool:
        """
        检查文章是否已存在（通过标题和单位名称）
        
        Args:
            title: 文章标题
            unit_name: 单位名称
            
        Returns:
            bool: 如果文章存在返回True，否则返回False
        """
        try:
            with self.connection.cursor() as cursor:
                sql = """SELECT id FROM fx_article_records 
                         WHERE article_title = %s AND unit_name = %s LIMIT 1"""
                cursor.execute(sql, (title, unit_name))
                result = cursor.fetchone()
                if result:
                    logger.debug(f"文章标题已存在: {title} (单位: {unit_name})")
                return result is not None
        except Exception as e:
            logger.error(f"检查文章标题是否存在时出错: {e}")
            return False
    
    def insert_article(self, article_data: Dict) -> bool:
        """
        插入文章到数据库
        
        Args:
            article_data: 文章数据字典，包含以下字段：
                - title: 文章标题
                - content: 文章内容
                - publish_time: 发布时间
                - url: 文章链接
                - account_name: 公众号名称
                - view_count: 浏览数（可选）
                - likes: 点赞数（可选）
                
        Returns:
            bool: 插入成功返回True，否则返回False
        """
        try:
            # 获取映射后的单位名称
            gzh_name = article_data.get('account_name', '')
            unit_name = self.get_unit_name(gzh_name)
            title = article_data.get('title', '')
            
            # 检查文章是否已存在（URL去重）
            if self.check_article_exists(article_data.get('url', '')):
                logger.info(f"文章URL已存在，跳过: {title}")
                return False
            
            # 检查文章标题是否已存在（标题去重）
            if title and self.check_article_exists_by_title(title, unit_name):
                logger.info(f"文章标题已存在，跳过: {title} (单位: {unit_name})")
                return False
            
            # 准备数据
            current_time = datetime.now()
            publish_time = article_data.get('publish_time', current_time)
            
            # 如果publish_time是时间戳，转换为datetime
            if isinstance(publish_time, (int, float)):
                publish_time = datetime.fromtimestamp(publish_time)
            elif isinstance(publish_time, str):
                try:
                    publish_time = datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                except:
                    publish_time = current_time
            
            article_id = self.generate_article_id(publish_time)
            
            with self.connection.cursor() as cursor:
                sql = """
                INSERT INTO fx_article_records (
                    crawl_time,
                    crawl_channel,
                    article_title,
                    article_content,
                    publish_time,
                    view_count,
                    article_url,
                    article_id,
                    create_time,
                    update_time,
                    likes,
                    share_count,
                    unit_name,
                    thumbs_count,
                    comments,
                    analysis
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """
                
                values = (
                    current_time,                              # crawl_time
                    "微信公众号",                               # crawl_channel
                    article_data.get('title', ''),             # article_title
                    article_data.get('content', ''),           # article_content
                    publish_time,                               # publish_time
                    article_data.get('view_count'),            # view_count
                    article_data.get('url', ''),               # article_url
                    article_id,                                 # article_id
                    current_time,                               # create_time
                    current_time,                               # update_time
                    article_data.get('likes'),                 # likes
                    article_data.get('share_count'),           # share_count
                    unit_name,                                  # unit_name (映射后的单位名称)
                    article_data.get('thumbs_count'),          # thumbs_count
                    article_data.get('comments'),              # comments
                    '0'                                         # analysis
                )
                
                cursor.execute(sql, values)
                self.connection.commit()
                
                logger.success(f"文章已保存到数据库: {article_data.get('title', '无标题')} (ID: {article_id})")
                return True
                
        except Exception as e:
            logger.error(f"插入文章到数据库时出错: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def batch_insert_articles(self, articles: List[Dict]) -> int:
        """
        批量插入文章
        
        Args:
            articles: 文章数据列表
            
        Returns:
            int: 成功插入的文章数量
        """
        success_count = 0
        for article in articles:
            if self.insert_article(article):
                success_count += 1
        
        logger.info(f"批量插入完成: 成功 {success_count}/{len(articles)} 篇")
        return success_count
    
    def get_latest_articles(self, account_name: str, limit: int = 10) -> List[Dict]:
        """
        获取某个公众号的最新文章
        
        Args:
            account_name: 公众号名称
            limit: 获取文章数量限制
            
        Returns:
            List[Dict]: 文章列表
        """
        try:
            with self.connection.cursor() as cursor:
                sql = """
                SELECT * FROM fx_article_records 
                WHERE unit_name = %s 
                ORDER BY publish_time DESC 
                LIMIT %s
                """
                cursor.execute(sql, (account_name, limit))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"获取最新文章时出错: {e}")
            return []
    
    def __enter__(self):
        """支持with语句"""
        self.connect()
        return self
    
    def record_crawl_completion(self, finished_date: datetime = None) -> bool:
        """
        记录爬虫循环完成时间到 fx_crawl_exception 表
        只保留最新的一条记录，删除之前的所有记录
        
        Args:
            finished_date: 完成时间，如果为None则使用当前时间
            
        Returns:
            bool: 记录成功返回True，否则返回False
        """
        try:
            if finished_date is None:
                finished_date = datetime.now()
            
            with self.connection.cursor() as cursor:
                # 先删除所有现有记录
                delete_sql = "DELETE FROM fx_crawl_exception"
                cursor.execute(delete_sql)
                
                # 插入新的记录
                insert_sql = """
                INSERT INTO fx_crawl_exception (
                    finished_date,
                    status,
                    create_time,
                    update_time
                ) VALUES (
                    %s, %s, %s, %s
                )
                """
                
                current_time = datetime.now()
                values = (
                    finished_date,     # finished_date
                    'finished',        # status (始终为finished)
                    current_time,      # create_time
                    current_time       # update_time
                )
                
                cursor.execute(insert_sql, values)
                self.connection.commit()
                
                logger.success(f"爬虫循环完成时间已更新: {finished_date.strftime('%Y-%m-%d %H:%M:%S')} (表中只保留最新记录)")
                return True
                
        except Exception as e:
            logger.error(f"记录爬虫循环完成时间时出错: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_latest_crawl_record(self) -> Optional[Dict]:
        """
        获取最新的爬虫循环记录（只有一条记录）
        
        Returns:
            Optional[Dict]: 最新的爬虫循环记录，如果没有记录返回None
        """
        try:
            with self.connection.cursor() as cursor:
                sql = "SELECT * FROM fx_crawl_exception LIMIT 1"
                cursor.execute(sql)
                result = cursor.fetchone()
                return result
        except Exception as e:
            logger.error(f"获取爬虫循环记录时出错: {e}")
            return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出with语句时关闭连接"""
        self.disconnect()


# 测试函数
def test_database():
    """测试数据库连接和操作"""
    with DatabaseManager() as db:
        # 测试插入文章
        test_article = {
            'title': '测试文章',
            'content': '这是测试内容',
            'publish_time': datetime.now(),
            'url': f'http://test.com/{random.randint(1000, 9999)}',
            'account_name': '测试公众号'
        }
        
        success = db.insert_article(test_article)
        if success:
            logger.success("数据库测试成功")
        else:
            logger.warning("数据库测试失败或文章已存在")


if __name__ == "__main__":
    test_database()
