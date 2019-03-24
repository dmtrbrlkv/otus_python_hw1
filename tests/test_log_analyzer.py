import unittest
import env

from log_analyzer import log_analyzer as la
import os.path
import datetime
import re

class Test_get_last_log_filepath(unittest.TestCase):
    test_dir = "test_dir"

    def setUp(self):
        if not os.path.exists(self.test_dir):
            os.mkdir(self.test_dir)
        with open(os.path.join(self.test_dir, "nginx-access-ui.log-20170630.gz"), 'w') as f:
            pass
        with open(os.path.join(self.test_dir, "nginx-access-ui.log-20170730.gz"), 'w') as f:
            pass
        with open(os.path.join(self.test_dir, "nginx-access-ui.log-20170801.bz2"), 'w') as f:
            pass
        with open(os.path.join(self.test_dir,"nginx-access-ui.log-20170830.gz"), 'w') as f:
            pass
        with open(os.path.join(self.test_dir,"report-20170830.html"), 'w') as f:
            pass

        la.load_config(la.config)
        self.log_file_template = la.config["LOG_FILE_TEMPLATE"]

    def tearDown(self):
        try:
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)
        except IOError:
            print("Не удалось почистить за собой")

    def test(self):
        res = la.get_last_log_filepath(self.test_dir,self.test_dir, self.log_file_template)
        self.assertEqual(res.filepath, os.path.join(self.test_dir, "nginx-access-ui.log-20170730.gz"))
        self.assertEqual(res.date, datetime.date(2017, 7, 30))


class Test_parse_log_string(unittest.TestCase):

    def test(self):
        test_log = []
        with open("testlog.txt") as f:
            for string in f:
                test_log.append(string.strip())

        parsed_log = []
        with open("parsedlog.txt") as f:
            for string in f:
                parsed_log.append(string.split())

        la.load_config(la.config)
        log_template = la.config["LOG_TEMPLATE_SIMPLE"]
        pattern = re.compile(log_template)

        for i, string in enumerate(test_log):
            res = la.parse_log_string(string, pattern)
            self.assertEqual(res.url, parsed_log[i][0])
            self.assertEqual(res.work_time, float(parsed_log[i][1]))

        res = la.parse_log_string("blablabla", pattern)
        self.assertEqual(res.url, None)
        self.assertEqual(res.work_time, None)


if __name__ == '__main__':
    unittest.main()
