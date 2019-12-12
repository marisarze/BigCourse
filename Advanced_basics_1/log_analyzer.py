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


CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log_samples"
}

RE_ROW_TEMPLATE = ' '.join([
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

RE_FILE_NAME = r'^nginx-access-ui.log-(?P<file_date>[0-9]{8})\.(gz|plain)'

FORMATTER = '[%(asctime)s] %(levelname)s %(message)s'
DATEFMT = '%Y.%m.%d %H:%M:%S'

def set_logging(path=None, formatter=FORMATTER, datefmt=DATEFMT, level=logging.INFO, restart=False):
    if restart:
        logging.getLogger().handlers = []
    formatter = logging.Formatter(formatter, datefmt)
    logging.getLogger().setLevel(level)
    if path:
        if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
        handler = logging.FileHandler(path)
        handler.setFormatter(formatter)
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)


def find_last_log(path, name_template=RE_FILE_NAME):
    try:
        logging.info('Поиск входных log-файлов в директории: {}'.format(path))
        file_names = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    except:
        logging.exception('Неверно указана входная директория log-файлов: {}'.format(path))
        sys.exit()

    file_names = [f for f in file_names if re.search(name_template,f)]
    if not file_names:
        logging.info('В директории входных логов отсутствуют файлы с шаблонным названием: {}.'.format(input_dir))
        sys.exit()
    return max(file_names)

def fix_config_values(config):
        """Исправляет значения ключей словаря конфигурации"""
        
        def check_positive(value):
            assert value>=0 
            return value
        
        logging.info('Проверка валидности значения ключей конфига')
        order = {
            "FAIL_PERC": (float, check_positive), 
            "LOG_DIR": (os.path.abspath,),
            "REPORT_DIR": (os.path.abspath,),
            "REPORT_SIZE": (int, check_positive),
            "OUT_LOG": (os.path.abspath,)
        }
        for key, funcs in order.items():
            if key in config.keys():
                try:
                    for func in funcs:
                        config[key] = func(config[key])
                except:
                    logging.exception('Некорректное значение поля "{}" в конфигурации'.format(key))


def get_new_config(path, old_config=None):
    """
    Возвращает дополненную версию словаря old_config, в который
    дописывается содержимое конфигурационного файла path. Данные 
    в файле path должны быть записаны в виде json-структуры или
    python-словаря.
    """

    if old_config == None:
        old_config = dict()
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


def parser(path, line_template=RE_ROW_TEMPLATE):
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
    line_format = re.compile(line_template, re.IGNORECASE)
    for line in input_file:
        data = re.search(line_format, line)
        if data:
            yield data.groupdict()
        else:
            yield None
    input_file.close()
    logging.info('Входной log-файл прочитан и закрыт')


def get_request_times_from_log(path):
    time_dict = dict()
    bad_count, good_count = 0, 0
    for entry in parser(path):
        if entry:
            dt = float(entry['request_time'])
            if entry['request_url'] in time_dict.keys():
                time_dict[entry['request_url']].append(dt)
            else:
                time_dict[entry['request_url']] = [dt]
            good_count += 1
        else:
            bad_count += 1
    return time_dict, good_count, bad_count


def get_stats(time_dict, size):
    time_sum = dict()
    all_time = 0.0
    N = 0
    for url in time_dict.keys():
        time_sum[url] = sum(time_dict[url])
        all_time += time_sum[url]
        N += len(time_dict[url])
    time_sorted = sorted(time_sum.items(), key=operator.itemgetter(1), reverse=True)
    out_list = list()
    logging.info('Вычисление выходных значений величин для таблицы отчета')
    for url, sum_value in time_sorted[:size]:
        n = len(time_dict[url])
        temp = sorted(time_dict[url])
        out_list.append({'count': n,
                        'time_avg': sum_value/n,
                        'time_max': max(time_dict[url]),
                        'time_sum': sum_value,
                        'url': url,
                        'time_med': (sum(temp[n//2-1:n//2+1])/2.0, temp[n//2])[n % 2] if n else None,
                        'time_perc': sum_value/all_time,
                        'count_perc': n/N
                        })
    return out_list


def round_values_in_list(target, number):
    logging.info('Округление значений величин для вставки в отчет...')
    for elem in target:
        for key in elem.keys():
            if isinstance(elem[key], float):
                elem[key] = round(elem[key], number)
    return target


def create_report(data_list, path):
    with open('report.html', 'r') as f:
            html_template = f.read()

    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(path, 'w') as out_report:
        html_out = Template(html_template).safe_substitute(table_json=str(data_list))
        out_report.write(html_out)
    logging.info('Результат отчета записаны в файл {}'.format(path))


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
                    превышение которого останавливает работу скрипта (по умолчанию 0.5)
        "OUT_LOG": путь выходного log-файл работы скрипта.

    В случае отсутствия опций запуска скрипт попытается считать конфигурационный файл
    из директории './configs/config.txt' относительно своего расположения, если операционной 
    системой является Windows, либо /usr/local/etc/ для Linux.
    Если конфигурационного файла нет в указанной директории по умолчанию,
    то скрипт завершает работу с ошибкой.
    """

    try:
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        set_logging()
        logging.info('Запуск скрипта...')
        config = CONFIG
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
            set_logging(config['OUT_LOG'])
            logging.info('Логгирование дополнительно ведется в файл {}'.format(config['OUT_LOG']))
            
        file_name = find_last_log(config['LOG_DIR'])
        file_date = re.search(RE_FILE_NAME, file_name).groupdict()['file_date']
        date_year = file_date[:4]
        date_month = file_date[4:6]
        date_day = file_date[6:8]
        if os.path.isfile(os.path.join(config['REPORT_DIR'],'report-{}.{}.{}.html'.format(date_year, date_month, date_day))):
            logging.info('Выходной отчет по последнему log-файлу уже существует.')
            sys.exit()
        
        full_name = os.path.join(config['LOG_DIR'], file_name)
        time_dict, good_count, bad_count  = get_request_times_from_log(full_name)

        if 'FAIL_PERC' in config.keys():
            fail_limit = config['FAIL_PERC'] * 100
            bad_percent = bad_count / (good_count+bad_count) * 100
            bad_percent = round(bad_percent, 3)
            fail_limit = round(fail_limit, 3)
            tmp_str = 'Доля неудачно обработанных строк во входном log-файле {}%, что {} допустимого {}%'
            tmp_str = tmp_str.format(bad_percent, '{}', fail_limit)
            if  bad_percent > fail_limit:
                logging.error(tmp_str.format('выше'))
                sys.exit()
            else:
                logging.info(tmp_str.format('ниже'))

        out_list = get_stats(time_dict, config['REPORT_SIZE'])
        out_list = round_values_in_list(out_list, 4)
        report_name = os.path.join(config['REPORT_DIR'], 'report-{}.{}.{}.html'.format(date_year, date_month, date_day))
        create_report(out_list, report_name)        
        logging.info('Работа скрипта успешно завершена.')
    except SystemExit:
        logging.info('Прерывание работы скрипта.')
    except:
        logging.exception('Неизвестная ошибка. Прерывание работы скрипта.')
    finally:
        logging.shutdown()



if __name__ == "__main__":
    main()