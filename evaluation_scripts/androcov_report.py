# analyze androcov result
# giving the instrumentation.json generated by androcov and the logcat generated at runtime
import os
import re
import json
import argparse
from datetime import datetime

# logcat regex, which will match the log message generated by `adb logcat -v threadtime`
LOGCAT_THREADTIME_RE = re.compile('^(?P<date>\S+)\s+(?P<time>\S+)\s+(?P<pid>[0-9]+)\s+(?P<tid>[0-9]+)\s+'
                                  '(?P<level>[VDIWEFS])\s+(?P<tag>[^:]*):\s+(?P<content>.*)$')


class Androcov(object):
    def __init__(self, androcov_dir):
        self.androcov_dir = androcov_dir
        instrumentation_file_path = os.path.join(self.androcov_dir, "instrumentation.json")
        self.instrumentation_detail = json.load(open(instrumentation_file_path))
        self.all_methods = set(self.instrumentation_detail['allMethods'])
        self.apk_path = self.instrumentation_detail['outputAPK']

    def gen_androcov_report(self, logcat_path):
        """
        generate a coverage report
        :param logcat_path:
        :return:
        """
        reached_methods, reached_timestamps = Androcov._parse_reached_methods(logcat_path)
        unreached_methods = self.all_methods - reached_methods
        androcov_report = {'reached_methods_count': len(reached_methods),
                           'unreached_methods_count': len(unreached_methods),
                           'all_methods_count': len(self.all_methods),
                           'coverage': "%.0f%%" % (100.0 * len(reached_methods) / len(self.all_methods)),
                           'uncoverage': "%.0f%%" % (100.0 * len(unreached_methods) / len(self.all_methods))}
        first_timestamp = reached_timestamps[0]
        time_scale = int((reached_timestamps[-1] - first_timestamp).total_seconds()) + 2
        timestamp_count = {}
        for timestamp in range(0, time_scale):
            timestamp_count[timestamp] = 0
        for reached_timestamp in reached_timestamps:
            delta_time = int((reached_timestamp - first_timestamp).total_seconds()) + 1
            timestamp_count[delta_time] += 1
        for timestamp in range(1, time_scale):
            timestamp_count[timestamp] += timestamp_count[timestamp - 1]
        androcov_report['timestamp_count'] = timestamp_count
        return androcov_report

    @staticmethod
    def _parse_reached_methods(logcat_path):
        reached_methods = set()
        reached_timestamps = []
        log_msgs = open(logcat_path).readlines()
        androcov_log_re = re.compile(r'^\[androcov\] reach \d+: (<.+>)$')
        for log_msg in log_msgs:
            log_data = Androcov.parse_log(log_msg)
            if log_data is None:
                continue
            log_content = log_data['content']
            # if 'androcov' not in log_content:
            #     continue
            m = re.match(androcov_log_re, log_content)
            if not m:
                continue
            reached_method = m.group(1)
            if reached_method in reached_methods:
                continue
            reached_methods.add(reached_method)
            reached_timestamps.append(log_data['datetime'])
        return reached_methods, reached_timestamps

    @staticmethod
    def parse_log(log_msg):
        """
        parse a logcat message
        the log should be in threadtime format
        @param log_msg:
        @return:
        """
        m = LOGCAT_THREADTIME_RE.match(log_msg)
        if not m:
            return None
        log_dict = {}
        date = m.group('date').strip()
        time = m.group('time').strip()
        log_dict['pid'] = m.group('pid').strip()
        log_dict['tid'] = m.group('tid').strip()
        log_dict['level'] = m.group('level').strip()
        log_dict['tag'] = m.group('tag').strip()
        log_dict['content'] = m.group('content').strip()
        datetime_str = "%s-%s %s" % (datetime.today().year, date, time)
        log_dict['datetime'] = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f")
        return log_dict


def parse_args():
    """
    parse command line input
    generate options
    """
    description = "Generate a report of coverage measured by androcov."
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-androcov", action="store", dest="androcov_dir", required=True,
                        help="path to androcov directory")
    parser.add_argument("-logcat", action="store", dest="logcat_path", required=True,
                        help="path to logcat file")
    options = parser.parse_args()
    # print options
    return options


if __name__ == "__main__":
    opts = parse_args()
    androcov = Androcov(androcov_dir=opts.androcov_dir)
    report = androcov.gen_androcov_report(opts.logcat_path)
    print json.dumps(report, indent=2)
