#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
第三方API客户端 - 获取文章阅读量、点赞量、在看量
==============================================

基于dsf_api.txt接口文档实现的API调用模块
"""

import requests
import time
import json
from typing import Dict, Optional, Tuple
from spider.log.utils import logger


class DSFApiClient:
    """第三方API客户端"""
    
    def __init__(self, api_key: str, verify_code: str = "", base_url: str = "https://www.dajiala.com"):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥
            verify_code: 附加码（如果设置了附加码则必须提供）
            base_url: API基础URL
        """
        self.api_key = api_key
        self.verify_code = verify_code
        self.base_url = base_url
        self.api_endpoint = f"{base_url}/fbmain/monitor/v3/read_zan"
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # QPS限制：不得高于5次/秒
        self.last_request_time = 0
        self.min_request_interval = 0.2  # 200ms间隔，确保不超过5次/秒
        
    def _wait_for_rate_limit(self):
        """等待满足QPS限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def get_article_stats(self, article_url: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        获取文章阅读量、点赞量、在看量
        
        Args:
            article_url: 微信文章链接
            
        Returns:
            Tuple[bool, Optional[Dict], Optional[str]]: 
                (成功标志, 数据字典, 错误信息)
                数据字典包含: {'read': int, 'zan': int, 'looking': int}
        """
        try:
            # 等待满足QPS限制
            self._wait_for_rate_limit()
            
            # 准备请求数据
            request_data = {
                "url": article_url,
                "key": self.api_key
            }
            
            # 如果设置了附加码，添加到请求中
            if self.verify_code:
                request_data["verifycode"] = self.verify_code
            
            logger.debug(f"请求API: {self.api_endpoint}")
            logger.debug(f"请求数据: {json.dumps(request_data, ensure_ascii=False)}")
            
            # 发送请求
            response = self.session.post(
                self.api_endpoint,
                json=request_data,
                timeout=30
            )
            
            # 检查HTTP状态码
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            logger.debug(f"API响应: {json.dumps(result, ensure_ascii=False)}")
            
            # 检查API返回的状态码
            code = result.get('code')
            msg = result.get('msg', '')
            
            if code == 0:
                # 成功
                data = result.get('data', {})
                stats = {
                    'read': data.get('read', 0),        # 阅读量
                    'zan': data.get('zan', 0),          # 点赞量
                    'looking': data.get('looking', 0)    # 在看量
                }
                
                cost_money = result.get('cost_money', 0)
                remain_money = result.get('remain_money', 0)
                
                logger.success(f"获取文章数据成功 - 阅读:{stats['read']} 点赞:{stats['zan']} 在看:{stats['looking']} "
                             f"消费:{cost_money}元 余额:{remain_money}元")
                
                return True, stats, None
                
            else:
                # API返回错误
                error_msg = self._get_error_message(code, msg)
                logger.warning(f"API返回错误 - 状态码:{code} 消息:{msg} 说明:{error_msg}")
                return False, None, error_msg
                
        except requests.exceptions.Timeout:
            error_msg = "请求超时"
            logger.error(f"API请求超时: {article_url}")
            return False, None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求异常: {str(e)}"
            logger.error(f"API请求异常: {error_msg}")
            return False, None, error_msg
            
        except json.JSONDecodeError as e:
            error_msg = f"响应JSON解析失败: {str(e)}"
            logger.error(f"API响应解析失败: {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"获取文章数据时发生未知错误: {error_msg}")
            return False, None, error_msg
    
    def _get_error_message(self, code: int, msg: str) -> str:
        """
        根据错误码获取错误说明
        
        Args:
            code: 错误码
            msg: 错误消息
            
        Returns:
            str: 错误说明
        """
        error_messages = {
            -1: "QPS超过上限，不得高于5次/秒，请5秒后再试！",
            101: "文章被删除或违规或公众号已迁移",
            105: "文章解析失败",
            106: "文章解析失败",
            107: "解析失败，请重试",
            10002: "key或附加码不正确",
            20001: "金额不足，请充值",
            20002: "请输入正确的微信链接",
            20003: "文章链接有误，请检查文章链接url中的&是否已经编码为%26",
            50000: "内部服务器错误"
        }
        
        if code in error_messages:
            return error_messages[code]
        elif msg == "Internal Server Error":
            return "网络错误，请重试1~3次"
        else:
            return f"未知错误码: {code}"
    
    def batch_get_article_stats(self, article_urls: list, max_retries: int = 3) -> Dict[str, Dict]:
        """
        批量获取多篇文章的数据
        
        Args:
            article_urls: 文章URL列表
            max_retries: 最大重试次数
            
        Returns:
            Dict[str, Dict]: URL为键，数据字典为值的结果
        """
        results = {}
        
        for i, url in enumerate(article_urls, 1):
            logger.info(f"处理文章 {i}/{len(article_urls)}: {url[:100]}...")
            
            # 重试机制
            for retry in range(max_retries):
                success, data, error = self.get_article_stats(url)
                
                if success:
                    results[url] = data
                    break
                else:
                    if retry < max_retries - 1:
                        wait_time = (retry + 1) * 2  # 递增等待时间
                        logger.warning(f"第{retry + 1}次尝试失败，{wait_time}秒后重试: {error}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"文章处理失败，已达最大重试次数: {error}")
                        results[url] = {"error": error}
            
            # 批量处理时的额外延迟
            if i < len(article_urls):
                time.sleep(0.5)  # 500ms间隔
        
        logger.info(f"批量处理完成: 成功 {len([r for r in results.values() if 'error' not in r])}/{len(article_urls)} 篇")
        return results


# 测试函数
def test_api_client():
    """测试API客户端"""
    # 注意：这里需要替换为真实的API密钥
    api_key = "your_api_key_here"
    
    client = DSFApiClient(api_key)
    
    # 测试URL（示例）
    test_url = "https://mp.weixin.qq.com/s?__biz=MjM5MTM5NjUzNA==&mid=2652494556&idx=1&sn=4995d845ad2ef1205136936f65ae4adc&chksm=bd5b5d058a2cd4139bbd92c8cd23d52f65ef260eedf8cbc6d25a4ab0992f08d01da81#rd"
    
    success, data, error = client.get_article_stats(test_url)
    
    if success:
        logger.success(f"测试成功: {data}")
    else:
        logger.error(f"测试失败: {error}")


if __name__ == "__main__":
    test_api_client()