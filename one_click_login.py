#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
一键登录脚本 - 自动打开浏览器扫码登录
"""

from login import WeChatSpiderLogin

def main():
    """主函数 - 执行登录"""
    print("🚀 微信公众号爬虫 - 一键登录")
    print("="*50)
    
    # 创建登录管理器
    login_manager = WeChatSpiderLogin()
    
    # 检查是否已登录
    if login_manager.is_logged_in():
        print("✅ 检测到有效登录，无需重新登录")
        print(f"Token: {login_manager.get_token()}")
        return
    
    # 开始登录
    print("📱 即将打开浏览器，请准备扫码...")
    input("按回车键继续...")
    
    if login_manager.login():
        print("🎉 登录成功！")
        print(f"Token: {login_manager.get_token()}")
        print("可以开始使用爬虫功能了！")
    else:
        print("❌ 登录失败，请重试")

if __name__ == "__main__":
    main()