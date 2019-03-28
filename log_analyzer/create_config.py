import json


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
            "HTML_TEMPLATE": "..\\reports\\report.html"
    }
    with open("config.json", mode="w") as f:
        json.dump(default_conf, f, indent=4)


if __name__ == '__main__':
    create_config_file()
