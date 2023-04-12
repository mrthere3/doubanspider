import os
import json
import re
import requests
from bs4 import BeautifulSoup
import time
from parsel import Selector
import pandas as pd

def login(ss, ua_headers):
    # 登录的网址
    basic_url = 'https://accounts.douban.com/j/mobile/login/qrlogin_code'
    # 提交的表单选项 
    data = {
        "ck": "",
    }
    # 正式登录
    try:
        print("准备扫码登录")
        response = ss.post(url=basic_url, headers=ua_headers, data=data)
        if re.search('\"status\":\"success\"', response.text):
            # 加载图片链接
            qrcode_url = json.loads(response.text)['payload']['img']
            print("请一定在2分钟内将下面的链接拷贝至浏览器打开，然后使用手机豆瓣app扫码：" + qrcode_url)
            print("因默认后台无提示，2分钟后将自动启动下载！")
            qrcode_name = re.findall(r"-qrlogin(.*)\.png", qrcode_url)[0]
            time.sleep(20)
            login_url = 'https://accounts.douban.com/j/mobile/login/qrlogin_status?ck=&code=douban-qrlogin' + qrcode_name
            ss.get(login_url, headers=ua_headers)
        return True
    except:
        return False

def get_discussions(ss, ua_headers, groupid, groupname):
    print("准备开始下载 {}_{} 小组的内容。".format(groupname, groupid))
    discussion_urls = list()
    # 开始访问小组页面
    group_url = 'https://www.douban.com/group/' + groupid + '/discussion?start=0&type=new'
    while True:
        response = ss.get(url=group_url, headers=ua_headers)
        # 获取小组页面中所有帖子的链接
        soup = BeautifulSoup(response.text,'html.parser')
        results = soup.find_all('td', attrs={'class': 'title'})
        for result in results:
            s_result = result.find('a')
            link = s_result['href']
            title = s_result['title']
            sc = result.find('span', attrs={'class': 'elite_topic_lable'})
            select = "精华" if sc else ""
            discussion_urls.append({'link': link, 'title': title, "select": select})
        # 查看是否有下一页，如果有的话需要继续访问下一页
        # next_page = soup.find('span', attrs={'class': 'next'})
        # if not next_page:
        #     break
        # next_link = next_page.find('a')
        # if not next_link:
        #     break
        # group_url = next_link['href']
        return discussion_urls
 
def save_discussions(ss, ua_headers,discussion_urls):
        csv_list = list()
        # 开始保存帖子
        index = 1
        for discussion_url in discussion_urls:
            print("[{}/{}]保存帖子：{}".format(index, len(discussion_urls), discussion_url['title']))
            # 保存一个帖子
            response = ss.get(discussion_url['link'], headers=ua_headers)
            time.sleep(1)
            soup = Selector(response.text)
            text = soup.xpath("//div[@class='rich-content topic-richtext']/p/text()").getall()[0] if soup.xpath(
                "//div[@class='rich-content topic-richtext']/p/text()").getall() else ""
            create_time = soup.xpath("//span[contains(@class,'create-time')]/text()").getall()[0] if soup.xpath(
                "//span[contains(@class,'create-time')]/text()").getall() else ""
            csv_list.append({"create_time": create_time, "title": discussion_url['title'], "text": text,
                             "select": discussion_url["select"], "link": discussion_url["link"]})
            index += 1
        return csv_list

def main():

    config = json.load(open('config.json', 'r', encoding="utf-8"))

    # 创建session保存登录状态
    ss = requests.Session()
    ua_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.3 Safari/605.1.15',
    }

    # 登录
    state = login(ss, ua_headers)
    result_list = list()
    # 携带登陆成功的cookie去请求
    if state:
        for group in config['grouplist']:
            groupid = group['groupid']
            groupname = group['groupname']
            discussion_urls = get_discussions(ss, ua_headers, groupid, groupname)
            result = save_discussions(ss, ua_headers,discussion_urls)
            result_list.extend(result)
        path = os.path.dirname(config["outputpath"])
        if not os.path.exists(path ):
            os.mkdir(path )
        pd1 = pd.DataFrame(result_list)
        pd1.to_excel(config["outputpath"],sheet_name="Sheet1",index=False)
    
    return

if __name__ == '__main__':
    main()

