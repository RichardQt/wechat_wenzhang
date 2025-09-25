import requests
import json
import time
import random
import ssl
import urllib3
import os # 新增
import re # 新增
from bs4 import BeautifulSoup # 新增

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

token = 910693565 # 76988585
cook = "ua_id=oSu8DmY0O8VPHxMXAAAAAJniiXuVOE-4vwgaMGuVhtc=; wxuin=44445675993456; mm_lang=zh_CN; qq_domain_video_guid_verify=25c4bec00ec9e81a; _qimei_uuid42=197070a1c0a1008735d8993dd04b0a3e5578e97bf2; pgv_pvid=4517729512; _qimei_fingerprint=f6412a507785e57dcc8384a5a08162ae; _qimei_q36=; _qimei_h38=8e291a3635d8993dd04b0a3e02000007519707; _clck=qgg5qq|1|fy8|0; uuid=d3ceacacced336afde9c23f8d04b9613; rand_info=CAESIHok/Sj/d3SulqeUUdk9QgX7rkPab7dBsdqo/1tVRsWl; slave_bizuin=3964274085; data_bizuin=3964274085; bizuin=3964274085; data_ticket=KUb1caiRv8arK0Bz+6XcsbZVZVuX6GOwaAwFFJNLDWKpf2Unhjxc0HupTRMf/sPM; slave_sid=ODJGNkN5VGxSSGRfTTZTUjhPQWswWjFsQmdWUWZ4cXIwWTdLcDFQbk5keERsQ19Ia2xTVFpXZGY1em82QTlUY1Q5eHlsanl3YlJfeFlJbDlMUTJtdERwaG9WSFR2ZlBsQ3FKT241blZQcXBGUmFlU25SbzFBMG5Nek9SZFRwWUlPWXlic0J5MjBIcUJZdzM2; slave_user=gh_53a2b06392f2; xid=0c4a7ccb719b3663199c0e5c03dfe41b; _clsk=1gheheo|1754457503823|3|1|mp.weixin.qq.com/weheat-agent/payload/record"
crawl_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}
title_pattern_crawl = re.compile(r'var msg_title = "([^"]+)"') # 重命名以避免与 get_cookie.py 中的变量冲突
date_pattern_crawl = re.compile(r'var ct = "(\d+)"')

get_cookie_header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    'Connection': 'close',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
}
cookie_dict = {
    'Cookie': cook
}

# 定义要爬取的公众号列表
accounts = ['机器之心']

# 搜索微信公众号的接口地址
search_url = 'https://mp.weixin.qq.com/cgi-bin/searchbiz?'

# JSON 数据文件路径
JSON_DATA_FILE = os.path.join('wechat_articles', 'articles_zijingzhisheng.json')
# 确保目录存在
os.makedirs('wechat_articles', exist_ok=True)


def load_crawled_articles():
    """加载已爬取的文章ID列表"""
    crawled_ids = set()
    if os.path.exists(JSON_DATA_FILE):
        try:
            with open(JSON_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for article in data.get("articles", []):
                    if 'id' in article:
                        crawled_ids.add(article['id'])
        except json.JSONDecodeError:
            print(f"警告: {JSON_DATA_FILE} 文件格式错误，将视为空文件。")
        except Exception as e:
            print(f"加载已爬取文章时出错: {e}")
    return crawled_ids

def append_article_to_json(article_data):
    """将单篇文章数据追加到JSON文件"""
    all_data = {"articles": []}
    if os.path.exists(JSON_DATA_FILE):
        try:
            with open(JSON_DATA_FILE, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
                if "articles" not in all_data or not isinstance(all_data["articles"], list):
                    all_data["articles"] = [] #确保articles字段存在且为列表
        except json.JSONDecodeError:
            print(f"警告: {JSON_DATA_FILE} 文件格式错误，将重新创建。")
            all_data = {"articles": []} # 如果文件损坏，则重新开始
        except Exception as e:
            print(f"读取JSON文件时出错: {e}, 将重新创建。")
            all_data = {"articles": []}


    all_data["articles"].append(article_data)

    try:
        with open(JSON_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"文章 '{article_data.get('title', 'N/A')}' 已追加到 {JSON_DATA_FILE}")
    except Exception as e:
        print(f"写入JSON文件时出错: {e}")


def extract_article_content_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    title_match = title_pattern_crawl.search(html_content)
    title = title_match.group(1) if title_match else "未知标题"

    date_match = date_pattern_crawl.search(html_content)
    raw_publish_time = date_match.group(1) if date_match else "0" # 默认为 "0"

    article_content_tag = soup.find(id="js_content")
    if article_content_tag:
        for tag in article_content_tag.find_all(True):
            tag.attrs = {} # 清理属性
        content_text = article_content_tag.get_text(separator='\n').strip() # 使用换行符分隔，更接近原文
    else:
        content_text = "无法提取内容"

    return {
        "title": title, # 这个title是从文章页面提取的，可能更准确
        "raw_publish_time": raw_publish_time,
        "content": content_text
    }

def crawl_and_save_single_article(article_meta, fakeid_for_log="N/A"):
    """爬取单篇文章内容并保存到JSON (修改自 crawl.py 的部分逻辑)"""
    print(f"尝试爬取文章: {article_meta['title']} (ID: {article_meta['id']})")
    try:
        response = requests.get(article_meta['link'], headers=crawl_headers, timeout=15, verify=False)
        if response.status_code == 200:
            article_details = extract_article_content_from_html(response.text)

            # 组合数据
            full_article_data = {
                "id": article_meta['id'],
                "title": article_meta['title'], # 使用列表页的标题
                "publish_date": article_meta['create_time_formatted'], # 使用列表页的时间
                "url": article_meta['link'],
                "content": article_details['content'],
                "raw_publish_time": article_details['raw_publish_time'], # 文章页提取的时间戳
                # 可以添加其他从 article_meta 中获取的元数据
                "cover": article_meta.get('cover', ''),
                "digest": article_meta.get('digest', ''),
                "source_fakeid": fakeid_for_log # 记录来源公众号的fakeid
            }
            append_article_to_json(full_article_data)
            return True
        else:
            print(f"爬取失败: {article_meta['title']}, 状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"请求文章时网络错误: {article_meta['title']}, 错误: {str(e)}")
        return False
    except Exception as e:
        print(f"处理文章时出错: {article_meta['title']}, 错误: {str(e)}")
        return False


import pickle

CRAWL_STATE_FILE = os.path.join('wechat_articles', 'crawl_state.pkl')

def load_crawl_state():
    """加载上次爬取的位置信息"""
    state = {}
    if os.path.exists(CRAWL_STATE_FILE):
        try:
            with open(CRAWL_STATE_FILE, 'rb') as f:
                state = pickle.load(f)
            print(f"已加载上次爬取状态: {state}")
        except Exception as e:
            print(f"加载爬取状态时出错: {e}")
    return state

def save_crawl_state(state):
    """保存当前爬取的位置信息"""
    try:
        with open(CRAWL_STATE_FILE, 'wb') as f:
            pickle.dump(state, f)
        print(f"已保存爬取状态: {state}")
    except Exception as e:
        print(f"保存爬取状态时出错: {e}")

def crawl_account_articles(word, max_articles_to_check=100, start_from=None):
    """
    爬取指定公众号的文章列表，并处理新文章
    
    参数:
    - word: 公众号名称
    - max_articles_to_check: 最多处理的文章数
    - start_from: 从哪个索引开始爬取 (None表示从最新的开始)
    """
    print(f"\n开始处理公众号: {word}")

    crawl_state = load_crawl_state()
    # 如果提供了start_from参数，它会覆盖保存的状态
    # 如果没有提供start_from且有保存的状态，使用保存的状态
    # 如果都没有，则从0开始
    if start_from is not None:
        begin = start_from
    elif word in crawl_state:
        begin = crawl_state.get(word, 0)
        print(f"从上次的位置继续爬取: begin={begin}")
    else:
        begin = 0
        print(f"没有找到上次爬取位置，从头开始爬取: begin={begin}")

    # 查询公众号的fakeid
    query_id = {
        'action': 'search_biz',
        'token': token,
        'lang': 'zh_CN',
        'f': 'json',
        'ajax': '1',
        'random': random.random(),
        'query': word,
        'begin': '0',
        'count': '5'
    }

    try:
        search_response = requests.get(search_url, cookies=cookie_dict, headers=get_cookie_header, params=query_id, verify=False, timeout=10)
        search_response.raise_for_status()
        search_data = search_response.json()
    except requests.exceptions.RequestException as e:
        print(f"搜索公众号 {word} 失败: {e}")
        return 0
    except json.JSONDecodeError:
        print(f"搜索公众号 {word} 返回非JSON内容: {search_response.text[:200]}")
        return 0

    lists = search_data.get('list', [])
    if not lists:
        print(f"未找到公众号: {word}")
        return 0

    fakeid = lists[0].get('fakeid')
    print(f"公众号 [{word}] 的fakeid: {fakeid}")

    crawled_article_ids = load_crawled_articles()
    print(f"已爬取 {len(crawled_article_ids)} 篇文章的ID。")
    
    new_articles_crawled_count = 0
    articles_processed_in_session = 0
    
    # 使用加载的begin值作为起点
    for k in range(begin, begin + max_articles_to_check, 5):
        if articles_processed_in_session >= max_articles_to_check:
            print(f"已检查达到 {max_articles_to_check} 条文章上限，停止检查公众号 {word}")
            # 保存当前位置+5（下次从下一批开始）
            crawl_state[word] = k + 5
            save_crawl_state(crawl_state)
            break

        print(f"正在获取公众号 [{word}] 第 {k} 到 {k+4} 条文章列表")
        list_url = f'https://mp.weixin.qq.com/cgi-bin/appmsg?token={token}&lang=zh_CN&f=json&ajax=1&random={random.random()}&action=list_ex&begin={k}&count=5&query=&fakeid={fakeid}&type=9'

        try:
            list_r = requests.get(url=list_url, headers=get_cookie_header, cookies=cookie_dict, verify=False, timeout=10)
            list_r.raise_for_status()
            list_data = list_r.json()
        except requests.exceptions.RequestException as e:
            print(f"获取文章列表失败 (公众号: {word}, 批次: {k}): {e}")
            time.sleep(random.uniform(5,10))
            continue
        except json.JSONDecodeError:
            print(f"获取文章列表返回非JSON内容 (公众号: {word}, 批次: {k}): {list_r.text[:200]}")
            time.sleep(random.uniform(5,10))
            continue

        app_msg_list_from_api = list_data.get("app_msg_list", [])
        articles_processed_in_session += len(app_msg_list_from_api)

        if not app_msg_list_from_api:
            print(f"公众号 [{word}] 没有更多文章或请求受限 (批次: {k})")
            # 保存当前位置（即使没有更多文章了，也记录这个位置）
            crawl_state[word] = k
            save_crawl_state(crawl_state)
            break

        # 处理这批文章
        for item in app_msg_list_from_api:
            article_id = item.get('aid', '')
            if not article_id:
                print(f"警告: 发现一个没有aid的文章项: {item.get('title', '无标题')}")
                continue

            if article_id not in crawled_article_ids:
                print('---------------------------------------')
                title = item.get("title", "无标题").replace('\n', '####')
                link = item.get("link", "")
                create_time_ts = item.get("create_time", 0)
                create_time_formatted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(create_time_ts))

                print(f"发现新文章: {title}")
                print(f"链接: {link}")

                article_meta_for_crawl = {
                    'id': article_id,
                    'title': title,
                    'link': link,
                    'create_time_formatted': create_time_formatted,
                    'cover': item.get('cover'),
                    'digest': item.get('digest')
                }

                if crawl_and_save_single_article(article_meta_for_crawl, fakeid):
                    new_articles_crawled_count += 1
                    crawled_article_ids.add(article_id)
                    delay = random.uniform(3, 7)
                    print(f"单篇文章爬取后等待 {delay:.2f} 秒...")
                    time.sleep(delay)
                else:
                    print(f"未能成功爬取或保存文章: {title}")
                    time.sleep(random.uniform(2,4))
            else:
                print(f"文章已存在: {item.get('title', '无标题')} (ID: {article_id})")

        # 每完成一批次，保存当前位置
        crawl_state[word] = k + 5  # 保存下一批次的起始位置
        save_crawl_state(crawl_state)
        
        batch_delay = random.uniform(4, 8)
        print(f"完成一批次文章列表处理，等待 {batch_delay:.2f} 秒...")
        time.sleep(batch_delay)

    print(f"公众号 [{word}] 处理完成，本轮新爬取 {new_articles_crawled_count} 篇文章")
    return new_articles_crawled_count

if __name__ == "__main__":
    total_new_crawled = 0
    
    import sys
    # 如果命令行提供了参数，使用它作为起始位置
    # 例如: python get_cookie.py 50
    start_position = None
    if len(sys.argv) > 1:
        try:
            start_position = int(sys.argv[1])
            print(f"从命令行参数指定的位置开始爬取: {start_position}")
        except ValueError:
            print(f"无效的起始位置参数: {sys.argv[1]}，将使用保存的状态或从头开始")
    
    for account_name in accounts:
        new_count = crawl_account_articles(account_name, max_articles_to_check=200, start_from=start_position)
        total_new_crawled += new_count
        
        if account_name != accounts[-1]:
            inter_account_sleep_time = random.randint(15, 30)
            print(f"公众号 [{account_name}] 处理完毕。休息 {inter_account_sleep_time} 秒后继续下一个公众号...")
            time.sleep(inter_account_sleep_time)
    
    print(f"\n所有公众号处理完成，共新爬取 {total_new_crawled} 篇文章。")