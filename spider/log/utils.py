#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志工具模块
===========

提供统一的日志记录功能
"""

from loguru import logger
import sys
import os

# 配置日志格式
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# 创建日志目录
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志输出
logger.remove()  # 移除默认的日志处理器

# 添加控制台输出
logger.add(
    sys.stdout,
    format=LOG_FORMAT,
    level="INFO",
    colorize=True
)

# 添加文件输出
logger.add(
    f"{log_dir}/wechat_crawler.log",
    format=LOG_FORMAT,
    level="DEBUG",
    rotation="10 MB",  # 当文件超过10MB时自动轮转到新文件
    retention="30 days",  # 保留7天的日志文件
    compression="zip",  # 压缩旧日志文件节省空间
    encoding="utf-8"
)

# 导出logger供其他模块使用
__all__ = ['logger']
