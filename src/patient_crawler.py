import logging
from logging.handlers import RotatingFileHandler

import re
from urllib.request import urlopen
from bs4 import BeautifulSoup

import json
import time

import pymysql

import mysql_patient_property

logging.Formatter.converter = time.gmtime
logger = logging.getLogger(__name__)
fileHandler = RotatingFileHandler('./log/patient_crawler.log', maxBytes=1024 * 1024 * 1024 * 9, backupCount=9)
fileHandler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)s] >> %(message)s'))
logger.addHandler(fileHandler)
logger.setLevel(logging.INFO)
logger.info('every package loaded and start logging')


def insert_result(data_list):
    connection = pymysql.connect(host=mysql_patient_property.hostname, user=mysql_patient_property.user,
                                 password=mysql_patient_property.password, db=mysql_patient_property.database,
                                 charset=mysql_patient_property.charset)
    cursor = connection.cursor(pymysql.cursors.DictCursor)

    for region_data_list in data_list:
        cursor.execute(f"delete from info_{region_data_list[0][0]};")
        cursor.execute(f"delete from path_{region_data_list[1][0]};")
        for data in region_data_list[0][1:]:
            cursor.execute(
                f"insert into info_{region_data_list[0][0]} values({data['patient_index']}, '{data['nationality']}', {data['sex']}, {data['age']}, '{data['causation']}', {data['confirmed_month']}, {data['confirmed_date']}, '{data['residence']}', '{data['clinic']}', {data['discharged']});")
        for data in region_data_list[1][1:]:
            cursor.execute(
                f"insert into path_{region_data_list[1][0]} values({data['patient_index']}, {data['path_no']}, {data['month']}, {data['date']}, '{data['content']}');")

    connection.commit()
    connection.close()


def dump_result(uid, data):
    with open('./patient-data/k_covid19_patient_' + str(uid) + '.json', 'w') as json_file:
        json.dump(data, json_file)


def get_busan_patient_path(target):
    logger.info('get_busan_patient_info: function started | target=' + target)

    downloaded_html = urlopen(target)
    logger.info('get_busan_patient_info: html downloaded')
    beautifulsoup_object = BeautifulSoup(downloaded_html, 'html.parser')
    logger.info('get_busan_patient_info: html parsed to beautifulsoup object')

    raw_patient_path_list_table = beautifulsoup_object.findAll('ul')
    # li', class_='result

    patient_path_list = ['busan']
    day_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    for raw_patient_path_table, patient_no in zip(
            reversed(raw_patient_path_list_table[2:len(raw_patient_path_list_table) - 4]),
            range(1, len(raw_patient_path_list_table) - 4)):
        raw_patient_path_beautifulsoup_object = BeautifulSoup(str(raw_patient_path_table), 'html.parser')
        raw_patient_path_list = raw_patient_path_beautifulsoup_object.findAll('li', class_='result')[0]

        raw_patient_path_list_beautifulsoup_object = BeautifulSoup(str(raw_patient_path_list), 'html.parser')

        for patient_path, path_no in zip(raw_patient_path_list_beautifulsoup_object.findAll('p'),
                                         range(len(raw_patient_path_list_beautifulsoup_object.findAll('p')))):
            if re.findall('<b>([^<]+)</b>', str(patient_path)):
                patient_path_text = re.sub('<p>', '', re.sub('</p>', '', re.sub('<b>([^<]+)</b>', '', str(patient_path)))).strip('​  \n')
                patient_path_date = re.findall('<b>([^<]+)</b>', str(patient_path))[0]

                if patient_path_text == '확인중':
                    continue
                elif re.findall('[0-9]+월[  ]*[0-9]+', patient_path_date):
                    month_period_identifier = re.findall('일\([월화수목금토일]\)[  ]*[~∼][  ]*[0-9]+([월])', patient_path_date)
                    date_period_identifier = re.findall('[  ]*[~∼][  ]*[0-9]+([일])', patient_path_date)
                    if month_period_identifier == ['월']:
                        start_month = int(re.findall('([0-9]+)[~월]', patient_path_date)[0])
                        start_date = int(re.findall('([0-9]+)[~일]', patient_path_date)[0])
                        end_month = int(re.findall('([0-9]+)[~월]', patient_path_date)[1])
                        end_date = int(re.findall('([0-9]+)[~일]', patient_path_date)[1])

                        for month in range(start_month, end_month + 1):
                            if month != end_month:
                                for date in range(start_date, day_in_month[month - 1] + 1):
                                    patient_path = {
                                        'patient_index': patient_no,
                                        'path_no': path_no,
                                        'month': month,
                                        'date': date,
                                        'content': patient_path_text
                                    }
                                    patient_path_list.append(patient_path)
                            else:
                                for date in range(start_date, end_date + 1):
                                    patient_path = {
                                        'patient_index': patient_no,
                                        'path_no': path_no,
                                        'month': month,
                                        'date': date,
                                        'content': patient_path_text
                                    }
                                    patient_path_list.append(patient_path)
                    elif date_period_identifier == ['일']:
                        month = int(re.findall('([0-9]+)[~월]', patient_path_date)[0])
                        start_date = int(re.findall('([0-9]+)[~일]', patient_path_date)[0])
                        end_date = int(re.findall('([0-9]+)[~일]', patient_path_date)[1])
                        for date in range(start_date, end_date + 1):
                            patient_path = {
                                'patient_index': patient_no,
                                'path_no': path_no,
                                'month': month,
                                'date': date,
                                'content': patient_path_text
                            }
                            patient_path_list.append(patient_path)
                    else:
                        patient_path = {
                            'patient_index': patient_no,
                            'path_no': path_no,
                            'month': int(re.findall('([0-9]+)월', patient_path_date)[0]),
                            'date': int(re.findall('([0-9]+)[일(월화수목금토일)]', patient_path_date)[0]),
                            'content': patient_path_text
                        }
                        patient_path_list.append(patient_path)
                else:
                    patient_path = {
                        'patient_index': patient_no,
                        'path_no': path_no,
                        'month': 0,
                        'date': 0,
                        'content': patient_path_text
                    }
                    patient_path_list.append(patient_path)

    return patient_path_list


def get_busan_patient_info(target):
    logger.info('get_busan_patient_info: function started | target=' + target)

    downloaded_html = urlopen(target)
    logger.info('get_busan_patient_info: html downloaded')
    beautifulsoup_object = BeautifulSoup(downloaded_html, 'html.parser')
    logger.info('get_busan_patient_info: html parsed to beautifulsoup object')

    raw_patient_info_list_table = beautifulsoup_object.findAll('ul')

    patient_info_list = ['busan']

    for raw_patient_info_table in reversed(raw_patient_info_list_table[2:len(raw_patient_info_list_table) - 4]):
        raw_patient_info_beautifulsoup_object = BeautifulSoup(str(raw_patient_info_table), 'html.parser')

        patient_info_elements = raw_patient_info_beautifulsoup_object.findAll('li')

        birth_year = int(re.findall('\([0-9][0-9]([0-9][0-9])년생/', patient_info_elements[0].text)[0])

        if birth_year < 20:
            age = 2020 - (birth_year + 2000)
        else:
            age = 2020 - (birth_year + 1900)

        patient_info = {
            'patient_index': int(re.findall('부산-([0-9]+)[  ]', patient_info_elements[0].text)[0]),
            'nationality': '한국',
            'sex': 1 if re.findall('년생/[  ]*([^/]+)/', patient_info_elements[0].text)[0] == '남' else 0,
            'age': age,
            'causation': patient_info_elements[1].text,
            'confirmed_month': 0 if patient_info_elements[4].text == '-' else int(
                re.findall('([0-9]+)/', patient_info_elements[4].text)[0]),
            'confirmed_date': 0 if patient_info_elements[4].text == '-' else int(
                re.findall('/([0-9]+)', patient_info_elements[4].text)[0]),
            'residence': re.findall('/[  ]*([^ /]+)\)', patient_info_elements[0].text)[0],
            'clinic': re.sub('\)', '', re.sub('퇴원\(', '', patient_info_elements[3].text)),
            'discharged': 1 if re.findall('퇴원\(', patient_info_elements[3].text) != [] else 0
        }

        patient_info_list.append(patient_info)

    return patient_info_list


def get_seoul_patient_path(target):
    logger.info('get_seoul_patient_info: function started | target=' + target)

    downloaded_html = urlopen(target)
    logger.info('get_seoul_patient_info: html downloaded')
    beautifulsoup_object = BeautifulSoup(downloaded_html, 'html.parser')
    logger.info('get_seoul_patient_info: html parsed to beautifulsoup object')

    raw_patient_path_list_table = beautifulsoup_object.findAll('td', class_='tdl')

    patient_path_list = ['seoul']
    day_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    for raw_patient_path_table, patient_no in zip(reversed(raw_patient_path_list_table),
                                                  range(1, len(raw_patient_path_list_table) + 1)):
        raw_patient_path_beautifulsoup_object = BeautifulSoup(str(raw_patient_path_table), 'html.parser')

        for patient_path, path_no in zip(raw_patient_path_beautifulsoup_object.findAll('li'),
                                         range(len(raw_patient_path_beautifulsoup_object.findAll('li')))):
            patient_path_text = patient_path.text.strip('​  \n')

            if patient_path_text == '확인중':
                continue
            elif re.findall('[0-9]+월[  ][0-9]+', patient_path_text):
                month_period_identifier = re.findall('일[  ~∼]+[0-9]+([월])', patient_path_text)
                date_period_identifier = re.findall('[  ~∼]+[0-9]+([일])', patient_path_text)
                if month_period_identifier == ['월']:
                    start_month = int(re.findall('([0-9]+)월[  ]', patient_path_text)[0])
                    start_date = int(re.findall('[  ]([0-9]+)일[  ~∼]+', patient_path_text)[0])
                    end_month = int(re.findall('[  ~∼]+([0-9]+)월[  ]', patient_path_text)[0])
                    end_date = int(re.findall('[  ]([0-9]+)일', patient_path_text)[0])

                    for month in range(start_month, end_month + 1):
                        if month != end_month:
                            for date in range(start_date, day_in_month[month - 1] + 1):
                                patient_path = {
                                    'patient_index': patient_no,
                                    'path_no': path_no,
                                    'month': month,
                                    'date': date,
                                    'content': patient_path_text
                                }
                                patient_path_list.append(patient_path)
                        else:
                            for date in range(start_date, end_date + 1):
                                patient_path = {
                                    'patient_index': patient_no,
                                    'path_no': path_no,
                                    'month': month,
                                    'date': date,
                                    'content': patient_path_text
                                }
                                patient_path_list.append(patient_path)
                elif date_period_identifier == ['일']:
                    month = int(re.findall('([0-9]+)월[  ]', patient_path_text)[0])
                    start_date = int(re.findall('[  ]([0-9]+)[  ~∼일]+', patient_path_text)[0])
                    end_date = int(re.findall('[  ~∼]+([0-9]+)일', patient_path_text)[0])
                    for date in range(start_date, end_date + 1):
                        patient_path = {
                            'patient_index': patient_no,
                            'path_no': path_no,
                            'month': month,
                            'date': date,
                            'content': patient_path_text
                        }
                        patient_path_list.append(patient_path)
                else:
                    patient_path = {
                        'patient_index': patient_no,
                        'path_no': path_no,
                        'month': int(re.findall('([0-9]+)월[  ]', patient_path_text)[0]),
                        'date': int(re.findall('월[  ]([0-9]+)', patient_path_text)[0]),
                        'content': patient_path_text
                    }
                    patient_path_list.append(patient_path)
            else:
                patient_path = {
                    'patient_index': patient_no,
                    'path_no': path_no,
                    'month': 0,
                    'date': 0,
                    'content': patient_path_text
                }
                patient_path_list.append(patient_path)

    return patient_path_list


def get_seoul_patient_info(target):
    logger.info('get_seoul_patient_info: function started | target=' + target)

    downloaded_html = urlopen(target)
    logger.info('get_seoul_patient_info: html downloaded')
    beautifulsoup_object = BeautifulSoup(downloaded_html, 'html.parser')
    logger.info('get_seoul_patient_info: html parsed to beautifulsoup object')

    raw_patient_info_list_table = beautifulsoup_object.findAll('tr', class_='patient')

    patient_info_list = ['seoul']

    for raw_patient_info_table in reversed(raw_patient_info_list_table):
        raw_patient_info_beautifulsoup_object = BeautifulSoup(str(raw_patient_info_table), 'html.parser')

        patient_info_elements = raw_patient_info_beautifulsoup_object.findAll('td')

        birth_year = int(re.findall('[   ‵\']([0-9]+)\)', patient_info_elements[1].text)[0])

        if birth_year < 20:
            age = 2020 - (birth_year + 2000)
        else:
            age = 2020 - (birth_year + 1900)

        patient_info = {
            'patient_index': int(re.findall('([0-9]+)[^0-9]+', patient_info_elements[0].text)[0]),
            'nationality': re.findall('([^ (]+)인[  ]\(', patient_info_elements[1].text)[0],
            'sex': 1 if re.findall('\(([^,]+),', patient_info_elements[1].text)[0] == '남' else 0,
            'age': age,
            'causation': patient_info_elements[2].text,
            'confirmed_month': int(re.findall('([0-9]+)/', patient_info_elements[3].text)[0]),
            'confirmed_date': int(re.findall('/([0-9]+)', patient_info_elements[3].text)[0]),
            'residence': patient_info_elements[4].text,
            'clinic': re.sub('[  ]+퇴원[  ]+', '', patient_info_elements[5].text),
            'discharged': 1 if re.findall('[  ]+퇴원[  ]+', patient_info_elements[5].text) != [] else 0
        }

        patient_info_list.append(patient_info)

    return patient_info_list


def get_patient_data():
    logger.info('get_patient_data: function started')

    patient_list = []

    patient_seoul = [get_seoul_patient_info('http://www.seoul.go.kr/coronaV/coronaStatus.do'),
                     get_seoul_patient_path('http://www.seoul.go.kr/coronaV/coronaStatus.do')]
    patient_list.append(patient_seoul)

    patient_busan = [get_busan_patient_info('http://www.busan.go.kr/corona19/index'),
                     get_busan_patient_path('http://www.busan.go.kr/corona19/index')]
    patient_list.append(patient_busan)

    return patient_list


if __name__ == '__main__':
    timestamp = int(time.time())
    logger.info('recorded a time stamp | timestamp=' + str(timestamp))

    result = get_patient_data()

    dump_result(timestamp, result)
    logger.info('dump result | timestamp=' + str(timestamp) + ' | result=' + str(result))
    insert_result(result)
    logger.info('insert result | result=' + str(result))

