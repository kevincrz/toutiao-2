import requests,json,re,os,pymongo
from urllib.parse import urlencode
from fake_useragent import UserAgent
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
from hashlib import md5
from json.decoder import JSONDecodeError
from multiprocessing import Pool

ua = UserAgent()
header = {'User-Agent':ua.random}

client = pymongo.MongoClient('localhost',27017,connect=False)     #是括号()，而非中括号[]
Toutiao_DB = client['Toutiao']
Toutiao_sheet = Toutiao_DB['toutiao']

#请求详情页
def get_page_index(offset,keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 1
    }
    url = 'http://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        response = requests.Session().get(url,headers=header)
        if response.status_code == 200:
            res = response.text
            return res
        pass
    except RequestException:
        print('请求索引页失败')
        pass

#爬取详情页，获取每个组图链接
def parse_page_index(text):
    try:
        data = json.loads(text)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except JSONDecodeError:     #如果text为空，用json解析有问题时跳过
        pass

#请求每个组图链接
def get_page_detail(url):
    try:
        response = requests.session().get(url,headers=header)
        if response.status_code == 200:
            res = response.text
            return res
        pass
    except RequestException:
        print('请求详情页出错',url)
        pass

#爬取每个组团链接的信息（图片，标题，链接）
def parse_page_detail(html,url):
    soup = BeautifulSoup(html,'lxml')
    sel = soup.select('title')
    title = sel[0].get_text()  if sel else print('')
    images_pattern = re.compile('var gallery = (.*?);',re.S)
    result = re.search(images_pattern,html)
    if result:
        data = json.loads(result.group(1))
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:download_image(image)
            return {
                'title':title,
                'url':url,      #每个组图的url链接
                'images':images     #图片链接
            }

#存储到mongoDB
def save_to_mongo(result):
    if Toutiao_sheet.insert(result):
        print('存储成功',result)
        return True
    return False

#下载图片
def download_image(url):        #url为每张图片的链接
    print('正在下载',url)
    try:
        response = requests.Session().get(url,headers= header)
        if response.status_code == 200:
            save_image(response.content)
        pass
    except RequestException:
        print('请求图片错误',url)
        pass

#存储图片
def save_image(content):
    # new_dir = os.mkdir(os.getcwd() + '//pic')
    file_path = '{0}/{1}.{2}'.format(os.getcwd(),md5(content).hexdigest(),'jpg')
    print(file_path)
    if not os.path.exists(file_path):
        with open(file_path,'wb')as f:
            f.write(content)
            f.close()

#运行主程序
def main(offset):
    text = get_page_index(offset,'街拍')
    for url in parse_page_index(text):
        html = get_page_detail(url)
        if html:
            result = parse_page_detail(html,url)
            if result: save_to_mongo(result)
            # print(result)

if __name__ == '__main__':
    groups = [x*20 for x in range(0,21)]
    pool = Pool()
    pool.map(main,groups)
    pool.close()
