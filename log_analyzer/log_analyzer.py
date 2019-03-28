# !/usr/bin/env python
# -*- coding: utf-8 -*-

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
import functools
import sys
import traceback

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "../reports",
    "LOG_DIR": "../logs"
}


def debug_info(func):
    """decorator for logging functions call"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logging.debug(f"Call function {func.__name__} with arguments args={args}, kwargs={kwargs}")
        res = func(*args, **kwargs)
        return res
    return wrapper


LogInfo = namedtuple("LogInfo", "filepath, date")
ParsedUrl = namedtuple("ParsedUrl", "url, work_time")
ParsedData = namedtuple("ParsedData", "urls, total_logs, total_time, err_count")


@debug_info
def get_last_log(log_dir, log_template):
    """
    get last log filepath and date
    :param log_dir: logs directory
    :param report_dir: reports directory
    :param log_template: regexp for log filename
    :return: LogPath(filepath=<filepath> , date=<date>), None if no logs
    """

    last_date = None
    fp = ""
    pattern = re.compile(log_template)
    if not os.path.exists(log_dir):
        raise FileNotFoundError(f"Logs directory does not exist - {log_dir}")
    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if not os.path.isfile(filepath):
            continue
        res = re.match(log_template, filename)
        if not res:
            continue
        year, month, day = map(int, (res.group("year"), res.group("month"), res.group("day")))
        cur_date = date(year, month, day)
        if not last_date or cur_date > last_date:
            last_date = cur_date
            fp = filepath
    return LogInfo(fp, last_date)


def is_report_exist(report_dir, date):
    """
    check report existance for the specified date
    :param report_dir: reports directory
    :param date: log date
    :return: True if report exist
    """
    exist_report_path = os.path.join(report_dir, "report-" + date.strftime("%Y%m%d") + ".html")
    return os.path.exists(exist_report_path)


@debug_info
def get_parsed_data(filpath, template):
    """
    log parsing
    :param filpath: log file path
    :param template: regexp for log line
    :return: ParsedData(urls=<dict("url": "list(request_time1, request_time2...)")>, total_logs=<total logs count>, total_time=<total request time>, err_count=<error count>)
    """

    urls = dict()
    total_logs = 0
    total_time = 0
    err_count = 0
    for parsed_url in parse_log_strings(filpath, template):
        total_logs += 1
        if parsed_url is None:
            err_count += 1
        else:
            total_time += parsed_url.work_time
            if parsed_url.url not in urls:
                urls[parsed_url.url] = []
            urls[parsed_url.url].append(parsed_url.work_time)
        # logging.debug(parsed_url)
    return ParsedData(urls, total_logs, total_time, err_count)


@debug_info
def parse_log_strings(filepath, template):
    """
    generator for parse log
    :param filepath: log file path
    :param template: regexp for log line
    :return: ParsedUrl(url=<url>, work_time=<request time>)
    """
    pattern = re.compile(template)
    open_f = gzip.open if filepath.endswith('.gz') else open
    with open_f(filepath, mode="rb") as f:
        cnt = 0
        for string in f:
            string = string.decode("utf8")
            cnt += 1
            if (cnt % 100000) == 0:
                logging.info(f"{cnt} lines processed")
            parsed_url = parse_log_string(string, pattern)
            if parsed_url is None:
              logging.info(f"Unrecognized line '{string.strip()}'")
            yield parsed_url


def parse_log_string(string, pattern):
    """
    parse one log line
    :param string: line
    :param pattern: compiled pattern for log line
    :return: ParsedUrl(utl=<url>, work_time=<request time>)
    """
    res = re.match(pattern, string)
    if res:
        return ParsedUrl(res.group("request_url"), float(res.group("request_time")))
    else:
        return None


def make_report_json(parsed_data, total_logs, total_time, report_size):
    """
    calculation of indicators and translation to json
    :param parsed_data: parsed data
    :param total_logs: total log count
    :param total_time: total request time
    :param report_size: max report size
    :return: json string
    """
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


def render_html(json_data, report_dir, date, report_file="report.html"):
    """
    render html report
    :param json_data: json data
    :param report_dir: reports directory
    :param date: report date
    :param report_file: report template file
    :return: path to generated report
    """
    if not os.path.exists(report_file):
        raise RuntimeError(f"Report template file not found - {report_file}")
    with open(report_file) as f:
        html = f.read()
    html = Template(html).safe_substitute(table_json=json_data)
    filepath = os.path.join(config["REPORT_DIR"], f"report-{date.strftime('%Y%m%d')}.html")
    with open(filepath, mode='w') as f:
        f.write(html)
    return os.path.abspath(filepath)


def init_log(level=logging.INFO,
             filename=None,
             format="[%(asctime)s] %(levelname).1s %(message)s",
             datefmt="%Y.%m.%d %H:%M:%S"
             ):
    """
    logging initialization
    :param level: logging level
    :param filename: file for logging
    :param format: logging format
    :param datefmt: date format
    :return:
    """
    logging.basicConfig(format=format, datefmt=datefmt, level=level, filename=filename)


def get_config_path():
    """
    get config file path from command line
    :return: config file path
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=str, default="config.json", help="config file")
    namespace = parser.parse_args()
    return namespace.config


def load_config(config, filepath):
    """
    loading config, update config dict with values from config file
    :param config: dict for loadind config
    :param filepath: config file path
    """

    if not os.path.exists(filepath):
        raise FileNotFoundError("config file not found")
    with open(filepath) as f:
        conf_from_file = json.load(f)
        if not isinstance(conf_from_file, dict):
            raise TypeError("Wrong data format in config file")
        for key, value in conf_from_file.items():
            config[key] = value

    if "LOGGING_LEVEL" not in config:
        config["LOGGING_LEVEL"] = logging.INFO

    if "LOGGING_FILE" not in config:
        config["LOGGING_FILE"] = "log.log"


def error_logging(info):
    """
    error logging
    if logger not initialized, print error to stderr
    :param info: info for logging
    """
    if logging.getLogger().hasHandlers():
        logging.exception(info)
    else:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)


def main():
    load_config(config, get_config_path())
    init_log(config["LOGGING_LEVEL"], config["LOGGING_FILE"])
    logging.info("Work begin")
    log_info = get_last_log(config["LOG_DIR"], config["LOG_FILE_TEMPLATE"])

    if is_report_exist(config["REPORT_DIR"], log_info.date):
        logging.info("No logs to analyze")
        return

    parsed_data = get_parsed_data(log_info.filepath, config["LOG_TEMPLATE_SIMPLE"])

    if "MAX_ERRORS_PERC" in config:
        max_errors = config["MAX_ERRORS_PERC"]
    else:
        max_errors = 100

    if parsed_data.err_count / parsed_data.total_logs * 100 >= max_errors:
        logging.error("Maximum error rate exceeded")
        return

    json_data = make_report_json(parsed_data.urls, parsed_data.total_logs, parsed_data.total_time,
                                 config["REPORT_SIZE"])
    report_path = render_html(json_data, config["REPORT_DIR"], log_info.date, config["HTML_TEMPLATE"])
    logging.info(f"Report is generated - {report_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        error_logging("Work interrupted:")
    except Exception as e:
        error_logging("An error occurred:")

