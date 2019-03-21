import os
import re
from datetime import date
from collections import namedtuple
import gzip

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

LogPath = namedtuple("LogPath", "filepath, date")
ParsedUrl = namedtuple("ParsedUrl", "url, work_time")


def get_last_log_filepath(log_dir, report_dir, log_template=r"nginx-access-ui\.log-(\d\d\d\d)(\d\d)(\d\d)\.gz$|$"):
    last_date = None
    fp = ""
    pattern = re.compile(log_template)
    for filename in os.listdir(log_dir):
        if os.path.isfile(filename):
            res = re.match(log_template, filename)
            if res:
                year = int(res.group(1))
                month = int(res.group(2))
                day = int(res.group(3))
                cur_date = date(year, month, day)
                exist_report_path = os.path.join(report_dir, "report-" + cur_date.strftime("%Y%m%d") + ".html")
                if not os.path.exists(exist_report_path):
                    if not last_date or cur_date > last_date:
                        last_date = cur_date
                        fp = filename
    return LogPath(fp, last_date)


def parse_log_strings(filepath):
    template = r'.+] ".+ (?P<url>.+)HTTP.+(?P<work_time>\d\.\d*)$'
    pattern = re.compile(template)

    open_f = gzip.open if filepath.endswith('.gz') else open
    with open_f(filepath) as f:
        cnt = 0
        for string in f:
            cnt += 1
            # if cnt > 1000:
            #     return
            res = re.match(pattern, string.decode("utf8"))
            if res:
                yield ParsedUrl(res.group("url"), float(res.group("work_time")))
            else:
                yield ParsedUrl(None, None)


def main():
    lp = get_last_log_filepath(config["LOG_DIR"], config["REPORT_DIR"])
    if lp.filepath:
        err_count = 0
        urls = dict()
        for parsed_url in parse_log_strings(lp.filepath):
            if parsed_url.url:
                if parsed_url.url not in urls:
                    urls[parsed_url.url] = [0, 0]
                urls[parsed_url.url][0] += parsed_url.work_time
                urls[parsed_url.url][1] += 1
                print(parsed_url)
            else:
                err_count += 1

    urls_list = [[key, value[0], value[1]]for key, value in urls.items()]
    urls_list.sort(key=lambda x: x[2], reverse=True)
    print(urls_list)
if __name__ == "__main__":
    main()

