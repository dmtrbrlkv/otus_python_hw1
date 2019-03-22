import os
import re
from datetime import date
from collections import namedtuple
import gzip
from statistics import median
from string import Template
import json
import argparse
import logging


#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "../reports",
    "LOG_DIR": "./"
}

LogPath = namedtuple("LogPath", "filepath, date")
ParsedUrl = namedtuple("ParsedUrl", "url, work_time")
ParsedData = namedtuple("ParsedData", "urls, total_logs, total_time, err_count")


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
            # logging.info(parsed_url)
        else:
            err_count += 1
    return ParsedData(urls, total_logs, total_time, err_count)


def parse_log_strings(filepath):
    template = r'(?P<remote_addr>.+) (?P<remote_user>.+) (?P<http_x_real_ip>.+) \[(?P<time_local>.+)\] \"(?P<request_type>.+) (?P<request_url>.+) (?P<request_v>.+)\" (?P<status>.+) (?P<body_bytes_sent>.+) (?P<http_refer>.+) \"(?P<http_user_agent>.+)\" (?P<http_x_forwarded_for>.+) (?P<http_X_REQUEST_ID>.+) (?P<http_X_RB_USER>.+) (?P<request_time>.+)'
    pattern = re.compile(template)

    open_f = gzip.open if filepath.endswith('.gz') else open
    with open_f(filepath, mode="rb") as f:
        cnt = 0
        for string in f:
            string = string.decode("utf8")
            cnt += 1
            if (cnt % 1000) == 0:
                logging.info(f"обработано {cnt} строк")
            if cnt > 10000:
                 return
            res = re.match(pattern, string)
            if res:
                yield ParsedUrl(res.group("request_url"), float(res.group("request_time")))
            else:
                logging.info(string)
                yield ParsedUrl(None, None)


def make_report_json(parsed_data, total_logs, total_time, report_size):
    UrlsInfo = namedtuple("UrlsInfo", "url, work_time_list")
    urls_infos = []
    for url, work_time_list in parsed_data.items():
        urls_infos.append(UrlsInfo(url, work_time_list))

    urls_infos.sort(key=lambda url_info: sum(url_info.work_time_list), reverse=True)
    to_json = []
    for urls_info in urls_infos[:min(report_size, len(urls_infos))]:
        count = len(urls_info.work_time_list)
        time_sum = sum(urls_info.work_time_list)
        row = {
            "url": urls_info.url,
            "count": count,
            "count_perc": count / total_logs * 100,
            "time_sum": time_sum,
            "time_perc": time_sum / total_time * 100,
            "time_avg": time_sum / count,
            "time_max": max(urls_info.work_time_list),
            "time_med": median(urls_info.work_time_list)
        }
        to_json.append(row)
    return json.dumps(to_json)


def render_html(json_data, report_dir, date):
    with open(os.path.join(report_dir, "report.html")) as f:
        html = f.read()
    html = Template(html).safe_substitute(table_json=json_data)
    filepath = os.path.join(config["REPORT_DIR"], f"report-{date.strftime('%Y%m%d')}.html")
    with open(filepath, mode='w') as f:
        f.write(html)
    return filepath


def load_config(config):
    parser = argparse.ArgumentParser()
    parser.add_argument("-rd", "--report_dir", type=str, help="папка для отчетов")
    parser.add_argument("-ld", "--log_dir",type=str , help="папка с логами")
    parser.add_argument("-c", "--config",type=str, default="config.json", help="конфигурационный файл")
    parser.add_argument("-rs", "--report_size",type=str, help="размер отчета")
    namespace = parser.parse_args()
    for key, value in namespace.__dict__.items():
        if value:
            if key != "config":
                config[key.upper()] = value
    filepath = namespace.config
    if filepath:
        if os.path.exists(filepath):
            with open(filepath) as f:
                conf_from_file = json.load(f)
                if isinstance(conf_from_file, dict):
                    for key, value in conf_from_file.items():
                        config[key] = value
                else:
                    logging.error("Неверный формат данных в конфигурационном файле")

        else:
            logging.error("Конфигурационный файл не найден")


    if "LOGGING_LEVEL" in config:
        logging.basicConfig(level=config["LOGGING_LEVEL"])
    if "LOGGING_FILE" in config:
        logging.basicConfig(filename=config["LOGGING_FILE"])
        logging.basicConfig(filename=None)

    logging.basicConfig(filename=None)
    logging.info("test info")


def main():

    logging.basicConfig(filename="logtest.txt")
    logging.basicConfig(level=logging.DEBUG)
    logging.error("file")
    logging.basicConfig(filename=None)
    logging.error("stdout")


    logging.basicConfig(format="[%(asctime)s] %(levelname).1s %(message)s",
                        datefmt="%Y.%m.%d %H:%M:%S",
                        level=logging.INFO,
                        filename="log.log",
                        )
    try:
        load_config(config)
        raise ValueError("test error")
        log_filepath = get_last_log_filepath(config["LOG_DIR"], config["REPORT_DIR"])
        if log_filepath.filepath:
            parsed_data = get_parsed_data(log_filepath.filepath)

            if "MAX_ERRORS_PERC" in config:
                max_errors = config["MAX_ERRORS_PERC"]
            else:
                max_errors = 100

            if parsed_data.err_count / parsed_data.total_logs * 100 >= max_errors:
                logging.Error("Превышен максимальный процент ошибок при анализе логов")
            json_data = make_report_json(parsed_data.urls, parsed_data.total_logs, parsed_data.total_time, config["REPORT_SIZE"])
            report_path = render_html(json_data, config["REPORT_DIR"], log_filepath.date)
            logging.info(report_path)
        else:
            logging.info("Нет логов для анализа")
    except BaseException as e:
        logging.exception("В процессе работы произошла ошибка")

if __name__ == "__main__":
    main()

