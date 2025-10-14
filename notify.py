import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime, timedelta
import time
import hashlib
import argparse
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('token_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_current_token_hash():
    """获取当前token的哈希值，用于检测token是否发生变化
    
    Returns:
        str: token的MD5哈希值，如果无法获取则返回None
    """
    try:
        cache_file = 'wechat_cache.json'
        if not os.path.exists(cache_file):
            return None
            
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        token = cache_data.get('token')
        timestamp = cache_data.get('timestamp')
        
        if not token:
            return None
        
        # 使用token+timestamp组合生成哈希，确保token更新后能够检测到变化
        token_string = f"{token}_{timestamp}"
        return hashlib.md5(token_string.encode('utf-8')).hexdigest()
        
    except Exception as e:
        logging.error(f"获取token哈希时出错: {str(e)}")
        return None


def load_reminder_history():
    """加载提醒历史记录
    
    Returns:
        dict: 提醒历史记录数据
    """
    history_file = 'reminder_history.json'
    default_history = {
        "current_token_hash": None,
        "last_pre_expiry_reminder": None,
        "last_expired_reminder": None,
        "reminder_count": {
            "pre_expiry": 0,
            "expired": 0
        }
    }
    
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
                # 确保所有必需的字段存在
                for key in default_history:
                    if key not in history:
                        history[key] = default_history[key]
                return history
        else:
            logging.info("提醒历史文件不存在，创建新的历史记录")
            return default_history.copy()
    except Exception as e:
        logging.error(f"加载提醒历史时出错: {str(e)}")
        return default_history.copy()


def save_reminder_history(history):
    """保存提醒历史记录
    
    Args:
        history (dict): 要保存的历史记录数据
    
    Returns:
        bool: 保存是否成功
    """
    history_file = 'reminder_history.json'
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"保存提醒历史时出错: {str(e)}")
        return False


def should_send_reminder(reminder_type, history, current_token_hash):
    """判断是否应该发送提醒
    
    Args:
        reminder_type (str): 提醒类型 ('pre_expiry' 或 'expired')
        history (dict): 提醒历史记录
        current_token_hash (str): 当前token的哈希值
    
    Returns:
        bool: 是否应该发送提醒
    """
    try:
        # 如果token发生了变化，重置提醒历史
        if history.get('current_token_hash') != current_token_hash:
            logging.info("检测到token变化，重置提醒历史")
            history['current_token_hash'] = current_token_hash
            history['last_pre_expiry_reminder'] = None
            history['last_expired_reminder'] = None
            history['reminder_count']['pre_expiry'] = 0
            history['reminder_count']['expired'] = 0
            return True
        
        # 检查该类型的提醒是否已经发送过
        last_reminder_key = f'last_{reminder_type}_reminder'
        if history.get(last_reminder_key):
            logging.info(f"{reminder_type}类型的提醒已经发送过，跳过")
            return False
        
        return True
        
    except Exception as e:
        logging.error(f"判断提醒发送条件时出错: {str(e)}")
        return False


def record_reminder_sent(reminder_type, history):
    """记录提醒已发送
    
    Args:
        reminder_type (str): 提醒类型
        history (dict): 提醒历史记录
    """
    try:
        current_time = datetime.now().isoformat()
        last_reminder_key = f'last_{reminder_type}_reminder'
        
        history[last_reminder_key] = current_time
        history['reminder_count'][reminder_type] += 1
        
        logging.info(f"已记录{reminder_type}类型提醒发送: {current_time}")
        
    except Exception as e:
        logging.error(f"记录提醒发送时出错: {str(e)}")


def auto_check_and_notify():
    """自动检测token状态并发送提醒（如果需要且未发送过）
    
    Returns:
        dict: 检测和提醒结果
    """
    result = {
        'check_successful': False,
        'reminder_needed': False,
        'reminder_sent': False,
        'reminder_type': None,
        'message': '',
        'hours_remaining': None
    }
    
    try:
        logging.info("开始自动检测token状态...")
        
        # 检查token过期状态
        is_expiring, hours_remaining, expiry_time, reminder_type = check_token_expiry()
        result['check_successful'] = True
        result['hours_remaining'] = hours_remaining
        
        if not is_expiring:
            if hours_remaining is not None:
                days_remaining = hours_remaining / 24
                result['message'] = f"Token状态正常，剩余有效期：{days_remaining:.1f}天"
                logging.info(result['message'])
            else:
                result['message'] = "无法获取Token状态"
                logging.warning(result['message'])
            return result
        
        # Token需要提醒
        result['reminder_needed'] = True
        result['reminder_type'] = reminder_type
        
        # 获取当前token哈希和提醒历史
        current_token_hash = get_current_token_hash()
        if not current_token_hash:
            result['message'] = "无法获取token信息，跳过提醒"
            logging.error(result['message'])
            return result
        
        # 加载提醒历史
        history = load_reminder_history()
        
        # 判断是否需要发送提醒
        if should_send_reminder(reminder_type, history, current_token_hash):
            # 发送提醒
            logging.info(f"准备发送{reminder_type}类型提醒")
            success = send_token_expiry_notification(hours_remaining, expiry_time, reminder_type)
            
            if success:
                # 记录提醒已发送
                record_reminder_sent(reminder_type, history)
                save_reminder_history(history)
                
                result['reminder_sent'] = True
                if reminder_type == 'expired':
                    result['message'] = "Token已过期，提醒邮件已发送"
                else:
                    result['message'] = f"Token即将过期（剩余{hours_remaining:.1f}小时），提醒邮件已发送"
                logging.info(result['message'])
            else:
                result['message'] = "提醒邮件发送失败"
                logging.error(result['message'])
        else:
            result['message'] = f"{reminder_type}类型的提醒已发送过，跳过重复提醒"
            logging.info(result['message'])
        
        return result
        
    except Exception as e:
        result['message'] = f"自动检测过程中发生错误: {str(e)}"
        logging.error(result['message'])
        return result


def send_email_notification(subject, body, to_email, new_articles=None):
    """发送邮件通知"""
    # 读取邮箱配置
    if not os.path.exists('email_config.json'):
        print("邮箱配置文件不存在，无法发送通知")
        return False
        
    with open('email_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    from_email = config.get('from_email')
    password = config.get('password')
    smtp_server = config.get('smtp_server')
    smtp_port = config.get('smtp_port', 587)
    
    if not all([from_email, password, smtp_server, to_email]):
        print("邮箱配置不完整，无法发送通知")
        return False
    
    # 构建邮件
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # 添加正文
    msg.attach(MIMEText(body, 'html'))
    
    try:
        # 连接到SMTP服务器
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.login(from_email, password)
        
        # 发送邮件
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"发送邮件时出错: {str(e)}")
        return False


def check_token_expiry():
    """检查token是否即将过期
    
    Returns:
        tuple: (是否需要提醒, 剩余小时数, 过期时间, 提醒类型)
        提醒类型: 'expired' - 已过期, 'pre_expiry' - 过期前10小时提醒, None - 不需要提醒
    """
    try:
        # 读取缓存文件获取token信息
        cache_file = 'wechat_cache.json'
        if not os.path.exists(cache_file):
            print(f"缓存文件 {cache_file} 不存在")
            return False, None, None, None
            
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 获取token和时间戳
        token = cache_data.get('token')
        timestamp = cache_data.get('timestamp')
        
        if not token or not timestamp:
            print("缓存文件中缺少token或timestamp信息")
            return False, None, None, None
        
        # 将时间戳转换为datetime对象
        # Token有效期为96小时（4天）
        token_created_time = datetime.fromtimestamp(timestamp)
        TOKEN_VALID_HOURS = 96  # Token有效期（小时）
        expiry_time = token_created_time + timedelta(hours=TOKEN_VALID_HOURS)
        
        # 计算剩余时间（小时）
        current_time = datetime.now()
        time_remaining = expiry_time - current_time
        hours_remaining = time_remaining.total_seconds() / 3600
        
        # 根据新的提醒逻辑判断提醒类型
        if hours_remaining <= 0:
            # Token已过期
            return True, hours_remaining, expiry_time, 'expired'
        elif hours_remaining <= 10:
            # 剩余时间小于等于10小时（过期前提醒）
            return True, hours_remaining, expiry_time, 'pre_expiry'
        else:
            # 剩余时间大于10小时，不需要提醒
            return False, hours_remaining, expiry_time, None
            
    except Exception as e:
        print(f"检查token过期时出错: {str(e)}")
        return False, None, None, None


def send_token_expiry_notification(hours_remaining, expiry_time, reminder_type):
    """发送token即将过期的邮件提醒
    
    Args:
        hours_remaining: 剩余小时数
        expiry_time: 过期时间
        reminder_type: 提醒类型 ('expired', 'pre_expiry')
    """
    # 根据提醒类型构建邮件主题和内容
    if reminder_type == 'expired':
        subject = "【紧急】微信Token已过期"
        urgency_level = "已过期"
        action_text = "请立即登录微信公众号平台更新Token"
        box_class = "urgent-box"
    elif reminder_type == 'pre_expiry':
        subject = "【提醒】微信Token即将在10小时内过期"
        urgency_level = f"即将过期（剩余{hours_remaining:.1f}小时）"
        action_text = "请及时登录微信公众号平台更新Token"
        box_class = "warning-box"
    else:
        # 不应该到达这里
        return False
    
    # 构建邮件正文
    body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .warning-box {{
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
            }}
            .urgent-box {{
                background-color: #f8d7da;
                border: 2px solid #dc3545;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
            }}
            .info-box {{
                background-color: #d1ecf1;
                border: 2px solid #17a2b8;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
            }}
            h2 {{ color: #333; }}
            ul {{ line-height: 1.8; }}
            .action-required {{
                color: #dc3545;
                font-weight: bold;
                font-size: 1.1em;
            }}
        </style>
    </head>
    <body>
        <h2>微信公众号Token过期提醒</h2>
        
        <div class="{box_class}">
            <p><strong>状态：</strong>{urgency_level}</p>
            <p><strong>过期时间：</strong>{expiry_time.strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p><strong>当前时间：</strong>{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p><strong>剩余时间：</strong>{f'{hours_remaining:.1f}小时' if hours_remaining > 0 else '已过期'}</p>
        </div>
        
        <h3>需要采取的行动：</h3>
        <p class="action-required">{action_text}</p>
        
        <h3>更新Token的步骤：</h3>
        <ol>
            <li>登录微信公众号平台：<a href="https://mp.weixin.qq.com">https://mp.weixin.qq.com</a></li>
            <li>进入"开发" -> "基本配置"页面</li>
            <li>获取新的Access Token</li>
            <li>运行 <code>login.py</code> 或 <code>one_click_login.py</code> 脚本更新本地缓存</li>
            <li>验证新Token是否正常工作</li>
        </ol>
        
        <h3>重要提示：</h3>
        <ul>
            <li>Token有效期为96小时（4天）</li>
            <li>Token过期后，所有依赖Token的功能将无法正常工作</li>
            <li>包括文章抓取、阅读量更新等核心功能</li>
            <li>建议在Token过期前完成更新，避免服务中断</li>
        </ul>
        
        <hr>
        <p style="color: #666; font-size: 0.9em;">
            此邮件由微信公众号爬虫系统自动发送，请勿回复。<br>
            如有疑问，请联系系统管理员。
        </p>
    </body>
    </html>
    """
    
    # 读取邮件配置并发送
    email_config_file = 'email_config.json'
    
    # 如果邮件配置文件不存在，创建一个示例配置
    if not os.path.exists(email_config_file):
        sample_config = {
            "from_email": "your_email@example.com",
            "password": "your_password",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "to_email": "recipient@example.com",
            "comment": "请修改此配置文件，填入实际的邮箱信息"
        }
        with open(email_config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, ensure_ascii=False, indent=2)
        print(f"已创建邮件配置文件模板：{email_config_file}")
        print("请编辑此文件，填入实际的邮箱信息后重新运行")
        return False
    
    # 读取邮件配置
    with open(email_config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    to_email = config.get('to_email')
    
    if not to_email:
        print("邮件配置中缺少收件人地址")
        return False
    
    # 发送邮件
    success = send_email_notification(subject, body, to_email)
    
    if success:
        print(f"Token过期提醒邮件已发送至 {to_email}")
    else:
        print("发送Token过期提醒邮件失败")
    
    return success


def main():
    """主函数：检查token过期并发送提醒
    支持命令行参数：
    --auto: 自动模式，使用防重复提醒机制
    --manual: 手动模式，忽略提醒历史强制发送（默认）
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Token过期检查和提醒工具')
    parser.add_argument('--auto', action='store_true',
                       help='自动模式：使用防重复提醒机制，避免重复发送相同类型的提醒')
    parser.add_argument('--manual', action='store_true',
                       help='手动模式：忽略提醒历史，强制检查并发送提醒（默认模式）')
    parser.add_argument('--quiet', action='store_true',
                       help='静默模式：只输出关键信息')
    
    args = parser.parse_args()
    
    # 如果没有指定模式，默认使用手动模式
    if not args.auto and not args.manual:
        args.manual = True
    
    if not args.quiet:
        print("=" * 50)
        mode_text = "自动模式（防重复提醒）" if args.auto else "手动模式（强制检查）"
        print(f"开始检查Token过期状态... [{mode_text}]")
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
    
    if args.auto:
        # 自动模式：使用防重复提醒机制
        result = auto_check_and_notify()
        
        if not args.quiet:
            if result['check_successful']:
                print(f"[成功] 检查完成: {result['message']}")
                if result['reminder_sent']:
                    print(f"[邮件] 提醒邮件已发送（类型：{result['reminder_type']}）")
                elif result['reminder_needed'] and not result['reminder_sent']:
                    print(f"[跳过] 提醒已跳过（类型：{result['reminder_type']}，防重复机制）")
            else:
                print(f"[失败] 检查失败: {result['message']}")
        
        return result['check_successful']
        
    else:
        # 手动模式：传统的强制检查方式
        is_expiring, hours_remaining, expiry_time, reminder_type = check_token_expiry()
        
        if is_expiring:
            if hours_remaining is not None and expiry_time is not None and reminder_type is not None:
                # 根据提醒类型显示不同的消息
                if reminder_type == 'expired':
                    if not args.quiet:
                        print(f"[警告] Token已过期！")
                elif reminder_type == 'pre_expiry':
                    if not args.quiet:
                        print(f"[警告] Token即将在10小时内过期！剩余时间：{hours_remaining:.1f}小时")
                
                if not args.quiet:
                    print(f"过期时间：{expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print("\n正在发送邮件提醒...")
                
                # 发送邮件提醒（手动模式忽略提醒历史）
                success = send_token_expiry_notification(hours_remaining, expiry_time, reminder_type)
                
                if not args.quiet:
                    if success:
                        print("[成功] 提醒邮件发送成功")
                    else:
                        print("[失败] 提醒邮件发送失败")
                
                return success
            else:
                if not args.quiet:
                    print("无法获取Token过期信息")
                return False
        else:
            if hours_remaining is not None and expiry_time is not None:
                # 转换为天数显示
                days_remaining = hours_remaining / 24
                if not args.quiet:
                    print(f"[正常] Token状态正常，剩余有效期：{days_remaining:.1f}天（{hours_remaining:.1f}小时）")
                    print(f"过期时间：{expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
            else:
                if not args.quiet:
                    print("无法获取Token状态")
                return False
        
        if not args.quiet:
            print("=" * 50)
            print("检查完成")
    

# 支持直接运行此脚本进行测试
if __name__ == "__main__":
    main()