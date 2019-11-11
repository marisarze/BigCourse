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

logging.basicConfig(format='[%(asctime)s] %(levelname)s %(message)s', 
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)
config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


default_config_dir = r'C:\Users\Tom\Documents\temp\config.txt'


def get_new_config(path, old_config):
    try:
        logging.info('Trying open file: %s' %path)
        config_file = open(path, 'r')
        logging.info('Trying read file: %s' %path)
        temp_str = config_file.read()
    except:
        logging.exception('Error occured when trying open or read the file in %s' %path)
        sys.exit()

    try:
        logging.info('Trying retrieve data from config file')
        priority_config = json.loads(temp_str)
    except:
        logging.exception('Error: Config file contains incorrect data')
        sys.exit()

    if priority_config:
        for key in priority_config.keys():
            old_config[key]=priority_config[key]
    return old_config

def parsing_generator(path):
    if path.endswith(".gz"):
        input_file = gzip.open(path)
    else:
        input_file = open(path)
    template = ' '.join([
        '(?P<remote_addr>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',  # '$remote_addr                       
        '(?P<remote_user>.+|\-)', #  $remote_user 
        '(?P<http_x_real_ip>\-|.+)', #   $http_x_real_ip 
        '\[(?P<time_local>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\]', # [$time_local] 
        '["](?P<request_type>[a-z]+)', # "$request_type '   
        '(?P<request_url>.+ HTTP\/1\.(1|0))["]', # $request_url" '
        '(?P<status>\d{3})', # '$status 
        '(?P<body_bytes_sent>\d+)', #   $body_bytes_sent 
        '["](?P<http_referer>(\-)|(.+))["]', # "$http_referer" '  
        '["](?P<http_user_agent>(\-)|(.+))["]', # '"$http_user_agent"
        '["](?P<http_x_forwarded_for>(\-)|(.+))["]', #  "$http_x_forwarded_for"
        '["](?P<http_x_request_id>(\-)|(.+))["]', #  "$http_X_REQUEST_ID"
        '["](?P<http_x_rb_user>(\-)|(.+))["]', #  "$http_X_RB_USER" '
        '(?P<request_time>(\-)|(.+))' # '$request_time'; 
    ])
    line_format = re.compile(template, re.IGNORECASE)
    for line in input_file:
        data = re.search(line_format, line)
        if data:
            data = data.groupdict()


def main():
    if '--config' in sys.argv:
        config_dir = sys.argv[sys.argv.index('--config')+1]
    else:
        config_dir = default_config_dir

    config = get_new_config(config_dir, config)
    if 'OUT_LOG' in config.keys():
        logging.info('Setting logging output to %s' %config['OUT_LOG'])
        logging.basicConfig(filename=config['OUT_LOG'], 
                    format='[%(asctime)s] %(levelname)s %(message)s', 
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)


    input_dir = config["LOG_DIR"]
    file_names = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    file_names = [f for f in file_names if re.search("^nginx-access-ui.log-[0-9]{8}\.(gz|plain)",f)]
    if file_names:
        file_name = os.path.join(input_dir, max(file_names))


    
    time_list = dict()
    all_lines = logfile.readlines()
    bad_count = 0
    good_count = 0
    all_time = 0.0
    for line in all_lines:
        data = re.search(line_format, line)
        if data:
            data = data.groupdict()
            dt = float(data['request_time'])
            if data['request_url'] in time_list.keys():
                time_list[data['request_url']].append(dt)
            else:
                time_list[data['request_url']] = [dt]
            all_time += dt
            good_count += 1
        else:
            bad_count += 1
        print bad_count+good_count, line

    for key in time_list.keys():
        count[key] = len(time_list[key])
        count_perc[key] = count[key]//good_count
        time_sum[key] = sum(time_list[key])
        time_perc[key] = time_sum[key]//all_time
        time_avg[key] = time_sum[key]//count[key]
        time_max[key] = max(time_sum[key])
        temp_sorted = sorted(time_list[key])
        n = count[key]
        time_med[key] = (sum(temp_sorted[n//2-1:n//2+1])/2.0, temp_sorted[count[key]//2])[n % 2] if n else None
    print len(time_list.keys())
    logfile.close()




if __name__ == "__main__":
    main()