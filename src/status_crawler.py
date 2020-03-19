import logging
from logging.handlers import RotatingFileHandler

import re
from urllib.request import urlopen
from bs4 import BeautifulSoup
import datetime

import json
import time

import pymysql
import mysql_status_property

logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)
fileHandler = RotatingFileHandler('./log/status_crawler.log', maxBytes=1024 * 1024 * 1024 * 9, backupCount=9)
fileHandler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)s] >> %(message)s'))
logger.addHandler(fileHandler)
logger.setLevel(logging.INFO)
logger.info("every package loaded and start logging")


def insert_result(uid, data_list):
    logger.info("insert_result: function started")
    connection = pymysql.connect(host=mysql_status_property.hostname, user=mysql_status_property.user,
                                 password=mysql_status_property.password, db=mysql_status_property.database,
                                 charset=mysql_status_property.charset)
    logger.info("insert_result: database connection opened")
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    logger.info("insert_result: database cursor created")

    for data in data_list[1:]:
        cursor.execute(
            f"insert into status_{data['region']} values({uid}, {data_list[0]}, {data['increased']}, {data['certified']}, {data['deisolation']}, {data['dead']}, {data['percentage']});")
        logger.info("insert_result: status_" + str(data['region']) + " data inserted | data=" + str(data))

    connection.commit()
    logger.info("insert_result: database connection commited")
    connection.close()
    logger.info("insert_result: database connection closed")

    logger.info("insert_result: function ended")


def dump_result(uid, data):
    logger.info("dump_result: function started")

    with open("./status-data/k_covid19_status_" + str(uid) + ".json", "w") as json_file:
        json.dump(data, json_file)
    logger.info(
        "dump_result: data dumped as " + "status-data/k_covid19_status_" + str(uid) + ".json | data=" + str(data))

    logger.info("dump_result: function ended")


def get_status_data(target=''):
    logger.info("get_status_data: function started | target=" + target)

    downloaded_html = urlopen(target)
    logger.info("get_status_data: html downloaded")
    beautifulsoup_object = BeautifulSoup(downloaded_html, "html.parser")
    logger.info("get_status_data: html parsed to beautifulsoup object")

    announced_time = ['2020',
                      re.findall('([0-9]+)[.]', beautifulsoup_object.findAll('p', class_='info')[0].text)[0],
                      re.findall('[.]([0-9]+)', beautifulsoup_object.findAll('p', class_='info')[0].text)[0],
                      re.findall('([0-9]+)시', beautifulsoup_object.findAll('p', class_='info')[0].text)[0]]
    logger.info("get_status_data: get announced time | announced_time=" + str(announced_time))

    datetime_object = datetime.datetime.strptime(str(announced_time), "['%Y', '%m', '%d', '%H']")
    logger.info("get_status_data: convert announced time to datetime object | datetime_object=" + str(datetime_object))
    announced_time_unix = int(time.mktime(datetime_object.timetuple()))
    logger.info(
        "get_status_data: convert datetime object to unix time | announced_time_unix=" + str(announced_time_unix))

    raw_table = beautifulsoup_object.findAll('tbody')
    logger.info("get_status_data: table picked out | raw_table=" + str(raw_table))
    raw_table_beautifulsoup_object = BeautifulSoup(str(raw_table[0]), "html.parser")
    logger.info("get_status_data: convert raw table to beautifulsoup object | raw_table_beautifulsoup_object=" + str(
        raw_table_beautifulsoup_object))
    table_data_rows = raw_table_beautifulsoup_object.findAll('tr')
    logger.info("get_status_data: export table data from raw_table_beautifulsoup_object | table_data_rows=" + str(
        table_data_rows))

    status_data_list = [announced_time_unix]
    logger.info("get_status_data: declare status_data_list | status_data_list=" + str(status_data_list))
    region_dictionary = {
        '합계': 'synthesize',
        '서울': 'seoul',
        '부산': 'busan',
        '대구': 'daegu',
        '인천': 'incheon',
        '광주': 'gwangju',
        '대전': 'daejeon',
        '울산': 'ulsan',
        '세종': 'sejong',
        '경기': 'gyeonggi',
        '강원': 'gangwon',
        '충북': 'chungbuk',
        '충남': 'chungnam',
        '전북': 'jeonbuk',
        '전남': 'jeonnam',
        '경북': 'gyeongbuk',
        '경남': 'gyeongnam',
        '제주': 'jeju',
        '검역': 'quarantine'
    }
    logger.info("get_status_data: declare region_dictionary | region_dictionary=" + str(region_dictionary))

    for table_data in table_data_rows:
        logger.info("get_status_data: extracting table data | table_data=" + str(table_data))
        table_data_beautifulsoup_object = BeautifulSoup(str(table_data), "html.parser")
        logger.info(
            "get_status_data: convert table_data to beautifulsoup object | table_data_beautifulsoup_object=" + str(
                table_data_beautifulsoup_object))

        region = region_dictionary[table_data_beautifulsoup_object.findAll('th')[0].text]
        logger.info("get_status_data: extracting region from table data | region=" + str(region))
        data = table_data_beautifulsoup_object.findAll('td')
        logger.info("get_status_data: extracting data from table data | data=" + str(data))

        status_data = {
            'region': region,
            'increased': int('0' + re.sub('[^0-9]', '', data[0].text)),
            'certified': int('0' + re.sub('[^0-9]', '', data[1].text)),
            'deisolation': int('0' + re.sub('[^0-9]', '', data[2].text)),
            'dead': int('0' + re.sub('[^0-9]', '', data[3].text)),
            'percentage': float('0' + re.sub('[^0-9.]', '', data[4].text))
        }
        logger.info("get_status_data: declare status data | status_data=" + str(status_data))

        status_data_list.append(status_data)
        logger.info(
            "get_status_data: put status data into status data list | status_data_list=" + str(status_data_list))

    logger.info("get_status_data: function ended | status_data_list=" + str(status_data_list))
    return status_data_list


if __name__ == '__main__':
    logger.info("start status_crawler.py")

    timestamp = int(time.time())
    logger.info("recorded a time stamp | timestamp=" + str(timestamp))

    result = get_status_data(target="http://ncov.mohw.go.kr/bdBoardList_Real.do?brdId=1&brdGubun=13")
    logger.info("get result | result=" + str(result))

    dump_result(timestamp, result)
    logger.info("dump result | timestamp=" + str(timestamp) + " | result=" + str(result))
    insert_result(timestamp, result)
    logger.info("insert result | timestamp=" + str(timestamp) + " | result=" + str(result))

    logger.info("end status_crawler.py")
