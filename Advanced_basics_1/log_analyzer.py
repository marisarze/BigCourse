#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

import sys
import os

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}


def main():
    if '--config' in sys.argv:
        config_dir = sys.argv[sys.argv.index('--config')+1]
    else:
        config_dir = config['LOG_DIR']
    
    try:
        config_file = open(config_dir, 'r')
    except:
        print "Could not read file:", config_dir
        
    


if __name__ == "__main__":
    main()