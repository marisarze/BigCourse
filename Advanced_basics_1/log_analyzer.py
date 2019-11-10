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

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}

default_config_dir = r'C:\Users\Tom\Documents\temp\config.txt'


def main():
    priority_config = {}
    if '--config' in sys.argv:
        config_dir = sys.argv[sys.argv.index('--config')+1]
    else:
        config_dir = default_config_dir
    
    try:
        config_file = open(config_dir, 'r')
        temp_str = config_file.read()
        #temp_str = temp_str.replace("\'", "\"")
        priority_config = json.loads(temp_str)
        print priority_config
    except:
        print 'Config file is not exist or corrupted'

    if priority_config:
        for key in priority_config.keys():
            config[key]=priority_config[key]    
    
    input_dir = config["LOG_DIR"]
    file_names = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
    file_names = [f for f in file_names if re.search("^nginx-access-ui.log-[0-9]{8}",f)]

    if file_names:
        input_file = max(file_names)
        if input_file.endswith(".gz"):
            logfile = gzip.open(os.path.join(input_dir, input_file))
        else:
            logfile = open(os.path.join(input_dir, input_file))

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

    count, count_perc, time_sum, time_perc, time_avg, time_max, time_med = {}, {}, {}, {}, {}, {}, {}
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