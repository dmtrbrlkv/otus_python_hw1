import os
import re
from datetime import date
from collections import namedtuple
import gzip
from statistics import median
from pprint import pprint
from string import Template
import json

#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "../reports",
    "LOG_DIR": "../ТЗ"
}

LogPath = namedtuple("LogPath", "filepath, date")
ParsedUrl = namedtuple("ParsedUrl", "url, work_time")


def get_last_log_filepath(log_dir, report_dir, log_template=r"nginx-access-ui\.log-(\d\d\d\d)(\d\d)(\d\d)\.gz$|$"):
    last_date = None
    fp = ""
    pattern = re.compile(log_template)
    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir,filename)
        if os.path.isfile(filepath):
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
                        fp = filepath
    return LogPath(fp, last_date)


def get_parsed_data(filpath):
    urls = dict()
    total_logs = 0
    total_time = 0
    err_count = 0
    for parsed_url in parse_log_strings(filpath):
        if parsed_url.url:
            if parsed_url.url not in urls:
                urls[parsed_url.url] = []
            urls[parsed_url.url].append(parsed_url.work_time)
            total_logs += 1
            total_time += parsed_url.work_time
            # print(parsed_url)
        else:
            err_count += 1
    return urls, total_logs, total_time


def parse_log_strings(filepath):
    template = r'.+] ".+ (?P<url>.+) HTTP/.+(?P<work_time>\d\.\d*)$'
    pattern = re.compile(template)

    open_f = gzip.open if filepath.endswith('.gz') else open
    with open_f(filepath, mode="rb") as f:
        cnt = 0
        for string in f:
            cnt += 1
            if cnt > 50000:
                 return
            res = re.match(pattern, string.decode("utf8"))
            if res:
                yield ParsedUrl(res.group("url"), float(res.group("work_time")))
            else:
                print(string)
                yield ParsedUrl(None, None)


def make_report_json(parsed_data, total_logs, total_time, report_size):
    urls_list = [[key, value] for key, value in parsed_data.items()]
    urls_list.sort(key=lambda x: sum(x[1]), reverse=True)
    to_json = []
    for u in urls_list[:min(report_size, len(urls_list))]:
        count = len(u[1])
        time_sum = sum(u[1])
        row = {
            "url": u[0],
            "count": count,
            "count_perc": count / total_logs * 100,
            "time_sum": time_sum,
            "time_perc": time_sum / total_time * 100,
            "time_avg": time_sum / count,
            "time_max": max(u[1]),
            "time_med": median(u[1])
        }
        to_json.append(row)
    return json.dumps(to_json)


def render_html(json_data, report_dir, date):
    with open(os.path.join(report_dir, "report.html")) as f:
        html = f.read()
    html = Template(html).safe_substitute(table_json=json_data)
    with open(os.path.join(config["REPORT_DIR"], f"report-{date.strftime('%Y%m%d')}.html"), mode='w') as f:
        f.write(html)


def main():
    lp = get_last_log_filepath(config["LOG_DIR"], config["REPORT_DIR"])
    if lp.filepath:
        parsed_data, total_logs, total_time = get_parsed_data(lp.filepath)
        json_data = make_report_json(parsed_data, total_logs, total_time, config["REPORT_SIZE"])
        render_html(json_data, config["REPORT_DIR"], lp.date)
    else:
        print("нет логов для анализа")

if __name__ == "__main__":
    main()

