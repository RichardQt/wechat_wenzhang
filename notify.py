import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os

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

def create_notification_for_new_articles(articles_data):
    """为新文章创建通知内容"""
    subject = f"微信公众号有{len(articles_data['articles'])}篇新文章"
    
    body = f"""
    <h2>{articles_data['account']}有新文章</h2>
    <p>抓取时间: {articles_data['crawl_time']}</p>
    <hr>
    <ul>
    """
    
    for article in articles_data['articles'][:10]:  # 最多显示10篇
        body += f"""
        <li>
            <h3>{article['title']}</h3>
            <p>发布时间: {article['create_time_str']}</p>
            <p>{article.get('digest', '无摘要')}</p>
            <p><a href="{article['link']}" target="_blank">阅读原文</a></p>
        </li>
        <hr>
        """
    
    if len(articles_data['articles']) > 10:
        body += f"<p>...等共{len(articles_data['articles'])}篇文章</p>"
    
    body += "</ul>"
    
    return subject, body