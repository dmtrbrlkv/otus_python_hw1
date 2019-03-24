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
    """декоратор для логирования вызовов функций"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logging.debug(f"Вызов функции {func.__name__} c аргументами args={args}, kwargs={kwargs}")
        res = func(*args, **kwargs)
        return res
    return wrapper


LogPath = namedtuple("LogPath", "filepath, date")
ParsedUrl = namedtuple("ParsedUrl", "url, work_time")
ParsedData = namedtuple("ParsedData", "urls, total_logs, total_time, err_count")

@debug_info
def get_last_log_filepath(log_dir, report_dir, log_template):
    """
    возвращает последний непроанализированный лог и его дату
    :param log_dir: папка с логами
    :param report_dir: папка с отчетами
    :param log_template: регулярное выражения для имени лог-файла
    :return: LogPath(filepath=<путь> , date=<дата>), если логов нет, то LogPath(None , None)
    """


    last_date = None
    fp = ""
    pattern = re.compile(log_template)
    if not os.path.exists(log_dir):
        raise RuntimeError(f"Не удалось открыть папку с логами - {log_dir}")
    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if os.path.isfile(filepath):
            res = re.match(log_template, filename)
            if res:
                year = int(res.group("year"))
                month = int(res.group("month"))
                day = int(res.group("day"))
                cur_date = date(year, month, day)
                exist_report_path = os.path.join(report_dir, "report-" + cur_date.strftime("%Y%m%d") + ".html")
                if not os.path.exists(exist_report_path):
                    if not last_date or cur_date > last_date:
                        last_date = cur_date
                        fp = filepath
    return LogPath(fp, last_date)

@debug_info
def get_parsed_data(filpath, template, max_log=None):
    """
    парсинг лога
    :param filpath: лог-файл
    :param template: регулярное выражение для строки лога
    :param max_log: максимальное число анализируемых строк
    :return: ParsedData(urls=<dict("url": "list(время1, время2...)")>, total_logs=<число логов>, total_time=<общее время обработки запросов>, err_count=<число ошибок>)
    """

    urls = dict()
    total_logs = 0
    total_time = 0
    err_count = 0
    for parsed_url in parse_log_strings(filpath, template, max_log):
        total_logs += 1
        if parsed_url.url:
            if parsed_url.url not in urls:
                urls[parsed_url.url] = []
            urls[parsed_url.url].append(parsed_url.work_time)
            total_time += parsed_url.work_time
        else:
            err_count += 1
        # logging.debug(parsed_url)
    return ParsedData(urls, total_logs, total_time, err_count)


@debug_info
def parse_log_strings(filepath, template, max_log=None):
    """
    вспомогательный генератор для парсинга, возвращает информацию для очередной проанализированной строки
    :param filepath: лог-файл
    :param template: регулярное выражение для строки лога
    :param max_log: максимальное число анализируемых строк
    :return: ParsedUrl(url=<url>, work_time=<время обработки запроса>)
    """
    pattern = re.compile(template)
    open_f = gzip.open if filepath.endswith('.gz') else open
    with open_f(filepath, mode="rb") as f:
        cnt = 0
        for string in f:
            string = string.decode("utf8")
            cnt += 1
            if (cnt % 100000) == 0:
                logging.info(f"обработано {cnt} строк")
            if max_log and cnt > max_log:
                return
            parsed_url = parse_log_string(string, pattern)
            if not parsed_url.url:
              logging.info(f"Нераспознанная строка {string.strip()}")
            yield parsed_url


def parse_log_string(string, pattern):
    """
    парсинг строки лога
    :param string: строка
    :param pattern: скомпилированный паттерн регулярного выражения для строки лога
    :return: ParsedUrl(utl=<url>, work_time=<время обработки запроса>)
    """
    res = re.match(pattern, string)
    if res:
        return ParsedUrl(res.group("request_url"), float(res.group("request_time")))
    else:
        return ParsedUrl(None, None)


def make_report_json(parsed_data, total_logs, total_time, report_size):
    """
    вычисления показателей и перевод распаршенной информации в json
    :param parsed_data: распаршенная информации
    :param total_logs: число логов
    :param total_time: общее время обработки запросов
    :param report_size: максимальный размер отчета
    :return: json строка
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
    рендер html отчета
    :param json_data: данные для отчета
    :param report_dir: папка для отчета
    :param date: дата отчета
    :param report_file: шаблон отчета
    :return: путь до сгенерированного отчета
    """
    if not os.path.exists(report_file):
        raise RuntimeError(f"Не найден файл шаблона отчета - {report_file}")
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
    инициализация логирования
    :param level: уровень лога
    :param filename: файл для лога
    :param format: формат записи лога
    :param datefmt: формат времени лога
    :return:
    """
    if not is_logging_init():
        logging.basicConfig(format=format, datefmt=datefmt, level=level, filename=filename)


def is_logging_init():
    """
    проинициализировано ли логирование
    :return:
    """
    return logging.getLogger().hasHandlers()


def load_config(config):
    """
    загрузака конфига, дополняет переданный конфиг значениями из параметров командной строки и конфиг-файла
    :param config: словарь, в который будет загружен конфиг
    """
    level = logging.INFO
    filename = None

    parser = argparse.ArgumentParser()
    parser.add_argument("-rd", "--report_dir", type=str, help="папка для отчетов")
    parser.add_argument("-ld", "--log_dir", type=str, help="папка с логами")
    parser.add_argument("-c", "--config", type=str, default="config.json", help="конфигурационный файл")
    parser.add_argument("-rs", "--report_size", type=str, help="размер отчета")
    parser.add_argument("-cc", "--create_config", action="store_true",
                        help="генерация дефолтного конфигурационного файла"
                        )
    namespace = parser.parse_args()

    if namespace.create_config:
        create_config_file()

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

    if "LOGGING_LEVEL" not in config:
        config["LOGGING_LEVEL"] = logging.INFO

    if "LOGGING_FILE" not in config:
        config["LOGGING_FILE"] = "log.log"



def create_config_file():
    """
    создание дефолтного конфиг-файла, если его случайно удалили
    """
    default_conf = {
            "LOG_FILE_TEMPLATE": "nginx-access-ui\\.log-(?P<year>\\d{4})(?P<month>\\d{2})(?P<day>\\d{2})\\.gz$|$",
            "LOG_TEMPLATE": ".+ .+ .+ \\[.+\\] \\\".+ (?P<request_url>.+) .+\\\" .+ .+ .+ \\\".+\\\" .+ .+ .+ (?P<request_time>.+)",
            "LOG_TEMPLATE_SIMPLE": ".+\\] \\\".+ (?P<request_url>.+) HTTP.+(?P<request_time>\\d\\.\\d*)$",
            "LOG_TEMPLATE_FULL": "(?P<remote_addr>.+) (?P<remote_user>.+) (?P<http_x_real_ip>.+) \\[(?P<time_local>.+)\\] \\\"(?P<request_type>.+) (?P<request_url>.+) (?P<request_v>.+)\\\" (?P<status>.+) (?P<body_bytes_sent>.+) (?P<http_refer>.+) \\\"(?P<http_user_agent>.+)\\\" (?P<http_x_forwarded_for>.+) (?P<http_X_REQUEST_ID>.+) (?P<http_X_RB_USER>.+) (?P<request_time>.+)",
            "MAX_ERRORS_PERC": 10,
            "MAX_LOGS": None,
            "HTML_TEMPLATE": "..\\reports\\report.html"
    }
    with open("config.json", mode="w") as f:
        json.dump(default_conf, f, indent=4)


def main():
    try:
        load_config(config)
        init_log(config["LOGGING_LEVEL"], config["LOGGING_FILE"])

        log_filepath = get_last_log_filepath(config["LOG_DIR"], config["REPORT_DIR"], config["LOG_FILE_TEMPLATE"])

        if not log_filepath.filepath:
            logging.info("Нет логов для анализа")
            return

        parsed_data = get_parsed_data(log_filepath.filepath, config["LOG_TEMPLATE_SIMPLE"], config["MAX_LOGS"])

        if "MAX_ERRORS_PERC" in config:
            max_errors = config["MAX_ERRORS_PERC"]
        else:
            max_errors = 100

        if parsed_data.err_count / parsed_data.total_logs * 100 >= max_errors:
            logging.error("Превышен максимальный процент ошибок при анализе логов")
            return

        json_data = make_report_json(parsed_data.urls, parsed_data.total_logs, parsed_data.total_time,
                                     config["REPORT_SIZE"])
        report_path = render_html(json_data, config["REPORT_DIR"], log_filepath.date, config["HTML_TEMPLATE"])
        logging.info(f"Отчет сформирован - {report_path}")

    except KeyboardInterrupt:
        init_log()
        logging.exception("Работа прервана")
    except Exception:
        init_log()
        logging.exception("В процессе работы произошла ошибка")


if __name__ == "__main__":
    main()
