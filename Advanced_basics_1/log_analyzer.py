#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import sys
import os
import json

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}

default_config_dir = r'/usr/local/etc/'

def main():
    if '--config' in sys.argv:
        config_dir = sys.argv[sys.argv.index('--config')+1]
    else:
        config_dir = default_config_dir
    
    try:
        config_file = open(default_config_dir, 'r')
        temp_str = config_file.read()
        temp_str = temp_str.replace("\'", "\"")
        priority_config = json.loads(temp_str)
    except:
        print (":", config_dir)

    if priority_config:
        for key in priority_config.keys():
            config[key]=priority_config[key]    
    
    input_dir = config["LOG_DIR"]
    file_names = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]


if __name__ == "__main__":
    main()