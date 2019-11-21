#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import sys
import os
import json
import re
import gzip
import logging
import operator
import platform
from string import Template


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def get_new_config(path, old_config):
    """

    Возвращает дополненную версию словаря old_config, в который
    дописано содержимое конфигурационного файла path. Данные 
    в файле path должны быть записаны в виде json-структуры или
    python-словаря.

    """

    try:
        with open(path, 'r') as config_file:
            temp_str = config_file.read().replace("\\", "/")
            logging.info('Чтение файла конфигурации из: {}'.format(path))
    except:
        logging.exception('Ошибка открытия или чтения файла {}'.format(path))
        sys.exit()

    try:
        priority_config = json.loads(temp_str)
        logging.info('Данные файла конфигурации успешно прочитаны')
    except:
        logging.exception('Файл конфигурации содержит некорректные данные')
        sys.exit()

    if priority_config:
        for key in priority_config.keys():
            old_config[key]=priority_config[key]
    logging.info('Конфигурация обновлена')
    return old_config


def parser(path):
    """
    
    Возвращает генератор, выдающий словарь распознанных значений
    параметров строки в log-файле path. Итерация проходит по строкам.
    В случае безуспешной попытки распозначить значения строки в файле 
    path возвращается None.

    """

    logging.info('Открыте входного log-файла для чтения: {}'.format(path))
    if path.endswith(".gz"):
        input_file = gzip.open(path)        
    else:
        input_file = open(path)
    line_template = ' '.join([
        '(?P<remote_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',                      
        '(?P<remote_user>.+|\-)',
        '(?P<http_x_real_ip>\-|.+)',
        '\[(?P<time_local>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\]', 
        '["](?P<request_type>[a-z]+)', 
        '(?P<request_url>.+ HTTP\/1\.(1|0))["]',
        '(?P<status>\d{3})',
        '(?P<body_bytes_sent>\d+)',
        '["](?P<http_referer>(\-)|(.+))["]',  
        '["](?P<http_user_agent>(\-)|(.+))["]',
        '["](?P<http_x_forwarded_for>(\-)|(.+))["]',
        '["](?P<http_x_request_id>(\-)|(.+))["]',
        '["](?P<http_x_rb_user>(\-)|(.+))["]',
        '(?P<request_time>(\-)|(.+))'
    ])
    line_format = re.compile(line_template, re.IGNORECASE)
    for line in input_file:
        data = re.search(line_format, line)
        if data:
            yield data.groupdict()
        else:
            yield None
    input_file.close()
    logging.info('Входной log-файл прочитан')


def main(options=sys.argv):
    """

    Скрипт создает отчет по обработке содержимого nginx log-файла. Параметры работы
    скрипта указываются при запуске в терминале через опцию --config path. В path находится
    конфигурационный файл в виде json-структуры. 

    Параметры, определяемые в конфигурационном файле:  
        "REPORT_SIZE": количество URL в отчете с наибольшим суммарным временем обработки
        "REPORT_DIR": выходная директория где создается отчет по работе скрипта 
        "LOG_DIR": директория, содержащая входные log-файлы для обработки
        "FAIL_PERC": верхнее допустимое отношение неудачно распознанных строк входного лога,
                    превышение которого останавливает работу скрипта (по умолчанию 0.1)
        "OUT_LOG": путь выходного log-файл работы скрипта.

    В случае отсутствия опций запуска скрипт попытается считать конфигурационный файл
    из директории './configs/config.txt' относительно своего расположения, если операционная
    система Windows, либо /usr/local/etc/ для Linux.
    Если конфигурационного файла нет в указанном или директории по умолчанию,
    то скрипт завершает работу с ошибкой.

    """
    try:
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', '%Y.%m.%d %H:%M:%S')
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logging.getLogger().handlers = []
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().addHandler(stream_handler)
        logging.info('Запуск скрипта...')
        config = {}
        fail_limit = 0.5
        input_dir = '.'
        out_report_dir = '.'
        default_config_dir = os.path.abspath(r'./configs/config.txt')
        if platform.system() == 'Linux':
            default_config_dir = r'/usr/local/etc/'
            

        if '--config' in options:
            config_dir = options[options.index('--config')+1]
            logging.info('Выбран внешний файл конфигурации')
        else:
            config_dir = default_config_dir
            logging.info('Опция --config не указана, выбран файл конфигурации по умолчанию')

        config = get_new_config(config_dir, config)
        if 'OUT_LOG' in config.keys():
            out_log = os.path.abspath(config['OUT_LOG'])
            logging.info('Логгирование дополнительно ведется в файл {}'.format(out_log))
            if not os.path.exists(os.path.dirname(out_log)):
                os.makedirs(os.path.dirname(out_log))
            file_handler = logging.FileHandler(out_log)
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)

        if 'FAIL_PERC' in config.keys():
            fail_limit = float(config['FAIL_PERC'])
        
        if 'LOG_DIR' in config.keys():
            input_dir = os.path.abspath(config['LOG_DIR'])
        
        if 'REPORT_DIR' in config.keys():
            out_report_dir = os.path.abspath(config['REPORT_DIR'])

        try:
            logging.info('Поиск входных log-файлов в директории: {}'.format(input_dir))
            file_names = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        except:
            logging.exception('Неверно указана входная директория log-файлов: {}'.format(input_dir))
            sys.exit()

        log_name_re = "^nginx-access-ui.log-(?P<file_date>[0-9]{8})\.(gz|plain)"
        file_names = [f for f in file_names if re.search(log_name_re,f)]

        if not file_names:
            logging.info('В директории входных логов отсутствуют файлы с шаблонным названием: {}.'.format(input_dir))
            sys.exit()

        file_name = max(file_names)
        file_date = re.search(log_name_re, file_name).groupdict()['file_date']
        date_year = file_date[:4]
        date_month = file_date[4:6]
        date_day = file_date[6:8]
        if os.path.isfile(os.path.join(out_report_dir,'report-{}.html'.format(file_date))):
            logging.info('Выходной отчет по последнему log-файлу уже существует.')
            sys.exit()
        
        time_dict = dict()
        bad_count, good_count = 0, 0
        all_time = 0.0
        full_name = os.path.join(input_dir, file_name)
        for entry in parser(full_name):
            if entry:
                dt = float(entry['request_time'])
                if entry['request_url'] in time_dict.keys():
                    time_dict[entry['request_url']].append(dt)
                else:
                    time_dict[entry['request_url']] = [dt]
                all_time += dt
                good_count += 1
            else:
                bad_count += 1

        bad_percent = bad_count / (good_count+bad_count) * 100
        fail_limit *= 100
        if  bad_percent > fail_limit:
            logging.error('Доля неудачно обработанных строк во входном log-файле {}%, что выше допустимого {}%'.\
                format(round(bad_percent, 3), round(fail_limit, 3)))
            sys.exit()
        else:
            logging.info('Доля неудачно обработанных строк во входном log-файле {}%, что ниже допустимого {}%'.\
                format(round(bad_percent, 3), round(fail_limit, 3)))

        time_sum = dict()
        for url in time_dict.keys():
            time_sum[url] = sum(time_dict[url])
        time_sorted = sorted(time_sum.items(), key=operator.itemgetter(1), reverse=True)
        out_list = list()
        logging.info('Вычисление выходных значений величин для таблицы отчета')
        for url, sum_value in time_sorted[:config['REPORT_SIZE']]:
            n = len(time_dict[url])
            temp = sorted(time_dict[url])
            out_list.append({'count': n,
                            'time_avg': sum_value/n,
                            'time_max': max(time_dict[url]),
                            'time_sum': sum_value,
                            'url': url,
                            'time_med': (sum(temp[n//2-1:n//2+1])/2.0, temp[n//2])[n % 2] if n else None,
                            'time_perc': sum_value/all_time,
                            'count_perc': n/good_count
                            })
        
        logging.info('Округление значений величин для вставки в отчет...')
        for elem in out_list:
            for key in elem.keys():
                if isinstance(elem[key], float):
                    elem[key] = round(elem[key], 4)

        with open('report.html', 'r') as f:
            html_template = f.read()
        if not os.path.exists(out_report_dir):
            os.makedirs(out_report_dir)
        out_report_name = os.path.join(out_report_dir, 'report-{}.{}.{}.html'.format(date_year, date_month, date_day))
        with open(out_report_name, 'w') as out_report:
            html_out = Template(html_template).safe_substitute(table_json=str(out_list))
            out_report.write(html_out)
        logging.info('Результат работы скрипта записан в файл {}'.format(out_report_name))
        logging.info('Работа скрипта успешно завершена.')
    except SystemExit:
        logging.info('Прерывание работы скрипта.')
    except:
        logging.exception('Неизвестная ошибка. Прерывание работы скрипта.')
    finally:
        logging.shutdown()



if __name__ == "__main__":
    main()