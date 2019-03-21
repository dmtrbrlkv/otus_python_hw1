import os
import re
from datetime import date
from collections import namedtuple

#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "../reports",
    "LOG_DIR": "../log_analyzer"
}

LogPath = namedtuple("LogPath", "date, filepath, ext")

def get_last_log_filepath(log_dir, report_dir, log_template=r"nginx-access-ui\.log-(\d\d\d\d)(\d\d)(\d\d)(\.gz$|$)"):
    last_date = None
    fp = ""
    ext = ""
    pattern = re.compile(log_template)
    for fname in os.listdir(log_dir):
        if os.path.isfile(fname):
            res = re.match(log_template, fname)
            if res:
                year = int(res.group(1))
                month = int(res.group(2))
                day = int(res.group(3))
                cur_date = date(year, month, day)
                exist_report_path = os.path.join(report_dir, "report-" + cur_date.strftime("%Y%m%d") + ".html")
                if not os.path.exists(exist_report_path):
                    if not last_date or cur_date > last_date:
                        last_date = cur_date
                        ext = res.group(4)
                        fp = fname
    return LogPath(fp, last_date, ext)

def main():
    lp = get_last_log_filepath(config["LOG_DIR"], config["REPORT_DIR"])
    print(lp)

if __name__ == "__main__":
    main()

