from bs4 import BeautifulSoup
import requests
import os
import re
import pymysql
import datetime as d
from threading import Thread
import queue
from time import sleep

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
}

def download_target_url(cnt_start, cnt_end, type_url='1-2-4-150', base_url='https://www.ziyuanhuan.com'):
    list_url = []
    for num in range(cnt_start, cnt_end):
        if num == 1:
            url = base_url + '/lm/' + type_url + '-0.html'
        else:
            url = base_url + '/lm/' + type_url + '-%d.html?tu=3' % num
        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
        # }
        req = requests.get(url=url, headers=headers)
        req.encoding = 'utf-8'
        html = req.text
        bf = BeautifulSoup(html, 'html.parser')
        targets_list = bf.find_all(class_='col-sm-6 col-md-12 beijing img-rounded ')
        for targar_url in targets_list:
            targar_url_1 = targar_url('a')[0]
            targar_url_2 = targar_url('a')[1]
            targar_url_3 = targar_url('a')[2]
            print('获取目录信息：' + re.sub('[\/:*?"<>|=]', '', targar_url_1['alt']).strip() + '=' + targar_url_1['href'])
            # print(targar_url_2.contents[2]) #作者
            # print(targar_url_3.contents[0]) #日期
            list_url.append(re.sub('[\/:*?"<>|=]', '', targar_url_1['alt']).strip() + '=' + targar_url_1['href'] + '=' +
                            targar_url_2.contents[2] + '=' + targar_url_3.contents[0])
    return list_url

def connect_targer_url(target_url, name, author, service_readingdate):
    try:
        txt_req = requests.get(url=target_url, headers=headers, timeout=5)
        txt_req.encoding = 'utf-8'
    except Exception as e:
        mysql_target_html_insert(name=name, url=target_url, parentid=1, author=author, readingStateCode=1,
                                 readingdate=d.datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                                 serviceReadingDate=service_readingdate)
        print('connect_targer_url' + e)
        return None
    else:
        id = mysql_target_html_insert(name=name, url=target_url, parentid=1, author=author, readingStateCode=0,
                                 readingdate=d.datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                                 serviceReadingDate=service_readingdate)
        return id, txt_req.text


def download_txt(target_url, filename, foldername, author, service_readingdate):
    txt_html_tuple = connect_targer_url(target_url=target_url, name=filename, author=author,
                                  service_readingdate=service_readingdate)
    if txt_html_tuple != None:
        filename_full = '\\' + foldername + '\\' + filename + '.txt'
        # id = txt_html_tuple[0]
        txt_html = txt_html_tuple[1]
        txt_bf = BeautifulSoup(txt_html, 'html.parser')
        txt_tag = txt_bf.find('div', id='demo')
        if foldername not in os.listdir():
            os.makedirs(foldername)
        if txt_tag != None:
            txt_txt = txt_tag.get_text('\n\t', 'br/')
            if filename + '.txt' not in os.listdir(foldername):
                file = open(os.getcwd() + filename_full, 'w', encoding='utf-8')
                file.write(txt_txt)
                print('已下载： ' + filename)
            else:
                print(filename + '已存在')

def download_img(target_url, name, foldername,author,service_readingdate):
    img_txt_tuple = connect_targer_url(target_url=target_url, name=name, author=author,
                                  service_readingdate=service_readingdate)
    if img_txt_tuple != None:
        img_txt = img_txt_tuple[1]
        id = img_txt_tuple[0]
        cnt = 1  # 子文件夹中图片名
        img_bf_1 = BeautifulSoup(img_txt, 'html.parser')
        img_urlTag = img_bf_1.find('div', id='demo')
        if foldername not in os.listdir():
            os.makedirs(foldername)
        if name not in os.listdir(foldername):
            os.makedirs(foldername + '/' + name)
        for img_url in img_urlTag('img'):
            img_url_1 = str((img_url['src']))
            filename = '/' + foldername + '/' + name + '/' + str(cnt) + '.jpg'
            # urlretrieve(url = img_url_1, filename= filename)  #403: Forbidden 该方法添加headers报错
            try:
                r = requests.get(img_url_1, stream=True, headers=headers,
                                 timeout=5)  # 如果要完善的话，可以根据img表中readingStateCode来选择timeout时间
            except Exception as e:
                print('download_img' + e)
                mysql_img_insert(parentid=id, name=str(cnt), url=img_url_1, readingStateCode=1)
            else:
                with open(filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=32):
                        f.write(chunk)
                mysql_img_insert(parentid=id, name=str(cnt), url=img_url_1, readingStateCode=0)
            cnt = cnt + 1


# 数据库目标html读数插入
def mysql_target_html_insert(name, url, parentid, author, readingStateCode, readingdate, serviceReadingDate):
    db = pymysql.connect("localhost", "root", "123456", "localdb",charset='utf8')
    cursor = db.cursor()
    id = mysql_target_html_selected(url = url)
    if id == 0:
        print('name:' + name + ' url:' + url + '已存入数据库')
    elif id > 0:
        sql = "insert into target_html(name, url, parentid, author, readingStateCode, readingdate, serviceReadingDate) values ('%s','%s',%d,'%s',%d,'%s','%s')" % (
            name, url, parentid, author, readingStateCode, readingdate, serviceReadingDate)
        try:
            cursor.execute(sql)
            db.commit()
        except Exception as e:
            print('mysql_target_html_insert' + str(e))
            db.rollback()
        else:
            new_id = cursor.lastrowid
            print(new_id)
            return new_id   #返回自增Id
        db.close()


# 数据库图片url读数插入
def mysql_img_insert(parentid, name, url, readingStateCode):
    db = pymysql.connect("localhost", "root", "123456", "localdb",charset='utf8')
    cursor = db.cursor()
    sql = "insert into img(name, url, parentid, readingStateCode) values ('%s','%s',%d,%d)" % (
        name, url, parentid, readingStateCode)
    try:
        cursor.execute(sql)
        db.commit()
    except Exception as e:
        print('mysql_img_insert' + e)
        db.rollback()
    db.close()

def mysql_target_html_selected(url):
    db = pymysql.connect("localhost", "root", "123456", "localdb",charset='utf8')
    cursor = db.cursor()
    sql = "select * from target_html where url = '%s'" % url
    try:
        cursor.execute(sql)
        if cursor.rowcount > 0:
            return cursor.fetchone()['Id']
        else:
            return 0
    except Exception as e:
        print('mysql_target_html_selected' + e)
        db.rollback()
    db.close()


if __name__ == '__main__':
    url_index = 'https://www.ziyuanhuan.com'
    type_url = '1-1-4-322'  # txt
    # type_url = '1-2-4-20'   #img
    # 分页循环下载＃
    page_add = 1
    cnt_start = 100
    for i in range(1, 300):
        cnt_end = cnt_start + page_add
        list = download_target_url(cnt_start=cnt_start, cnt_end=cnt_end, type_url=type_url, base_url=url_index)
        for each_txt in list:
            txt_info = each_txt.split('=')
            target_url = url_index + txt_info[1]
            filename = txt_info[0]
            author = txt_info[2]
            service_readingdate = txt_info[3]
            foldername = 'note3'
            download_txt(target_url=target_url, filename=filename, foldername=foldername, author=author,
                         service_readingdate=service_readingdate)
            # download_img(target_url=target_url, name=filename, foldername=foldername)
        cnt_start = cnt_end
