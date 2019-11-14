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
from string import Template

logging.basicConfig(format='[%(asctime)s] %(levelname)s %(message)s', 
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)
config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


default_config_dir = './configs'


def get_new_config(path, old_config):
    try:
        config_file = open(path, 'r')
        temp_str = config_file.read()
        logging.info('Сonfig file reading from: {}'.format(path))
    except:
        logging.exception('Error: can not open or read the file {}'.format(path))
        sys.exit()

    try:
        priority_config = json.loads(temp_str)
        logging.info('Config file data extracted')
    except:
        logging.exception('Error: Config file contains incorrect data')
        sys.exit()

    if priority_config:
        for key in priority_config.keys():
            old_config[key]=priority_config[key]
    logging.info('Configuration data updated')
    return old_config

def parser(path):
    logging.info('Opening log file for parsing {}'.format(path))
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
    logging.info('log file closed')


def main():
    logging.info('Starting execution of the script')
    tolerance = 0.8
    if '--config' in sys.argv:
        config_dir = sys.argv[sys.argv.index('--config')+1]
        logging.info('External config file preferred')
    else:
        config_dir = default_config_dir
        logging.info('Default configuration directory selected')

    config = get_new_config(config_dir, config)
    if 'OUT_LOG' in config.keys():
        logging.info('Setting logging output to {}'.format(config['OUT_LOG']))
        logging.basicConfig(filename=config['OUT_LOG'], 
                    format='[%(asctime)s] %(levelname)s %(message)s', 
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)
    if 'SUCCESS_PERC' in config.keys():
        tolerance = config['SUCCESS_PERC']
    input_dir = config['LOG_DIR']

    log_name_re = "^nginx-access-ui.log-(?P<file_date>[0-9]{8})\.(gz|plain)"
    file_names = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    file_names = [f for f in file_names if re.search(log_name_re,f)]

    if not file_names:
        logging.info('There is no any input log file in directory: {} \n Script is stopping.'.format(input_dir))
        sys.exit()

    file_name = max(file_names)
    file_date = re.search(log_name_re, file_name).groupdict()['file_date']
    if os.path.isfile(os.path.join(input_dir,'report-{}.html'.format(file_date))):
        logging.info('Output report file is already exist. Finishing execution.')
        sys.exit()
    
    time_dict = dict()
    bad_count, good_count = 0, 0
    all_time = 0.0
    full_name = os.path.join(input_dir, file_name)
    logging.info('Starting parsing...')
    for entry in parser(full_name):
        if entry:
            dt = entry['request_time']
            if entry['request_url'] in time_dict.keys():
                time_dict[entry['request_url']].append(dt)
            else:
                time_dict[entry['request_url']] = [dt]
            all_time += dt
            good_count += 1
        else:
            bad_count += 1

    if good_count/(good_count+bad_count) < tolerance:
        logging.error('Insufficient percentage of successfully processed lines \
                        for the further script running. Finishing execution.')
        sys.exit()

    time_sum = dict()
    for url in time_dict.keys():
        time_sum[url] = sum(time_dict[url])
    time_sorted = sorted(time_sum.item(), key=operator.itemgetter(1), reverse=True)
    out_list = list()
    logging.info('Calculation of output values')
    for url, sum_value in time_sorted[:config['REPORT_SIZE']]:
        n = len(time_dict[url])
        temp = sorted(time_dict[url])
        out_list.append({'count': n,
                        'time_avg': sum_value/n,
                        'time_max': max(time_dict[url]),
                        'time_sum': sum_value,
                        'url': url,
                        'time_med': (sum(temp[n/2-1:n/2+1])/2.0, temp[n/2])[n % 2] if n else None,
                        'time_perc': sum_value/all_time,
                        'count_perc': n/good_count
                        })
    
    html_template = open('report.html', 'r').read()
    out_report = open('report-{}.html'.format(file_date), 'w')
    html_out = Template(html_template).safe_substitute(table_json=str(out_list))
    out_report.write(html_out)
    out_report.close()
    logging.info('Log analysis completed successfully')
        



if __name__ == "__main__":
    main()