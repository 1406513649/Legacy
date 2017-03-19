#!/usr/bin/env python
import os
import re
import sys
import time
import glob
from os.path import isfile, isdir, join, expanduser

d = os.getenv('DOT_LOCAL', os.path.expanduser('~/.local.d'))
my_calendar_file = join(d, 'share/calendar/calendar.bsd')


def main():
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        sys.exit('''parse_calendar.py
usage: parse_calendar.py [-h,--help] [--gen]

Optional Arguments
==================
-h, --help Generate this help message and exit
--gen      Generate the calendar cache [default: False]
''')
    if '--gen' in argv and isfile(my_calendar_file):
        os.remove(my_calendar_file)
    today = time.strftime('%m/%d')
    print_the_days_events(today)
    return 0


def stringify(text, encoding='utf-8'):
    tabbed = text.startswith(b'\t')
    def str1(item):
        try:
            return str(item, encoding=encoding).strip()
        except:
            return str(item).strip()
    try:
        string = ' '.join('{0:s}'.format(str1(x)) for x in text.split())
    except TypeError:
        print(text)
        raise
    return tabbed, string


def split1(string):
    split_string = string.split()
    split_string = [split_string[0], ' '.join(split_string[1:])]
    return [x for x in split_string if x.split()]


def find_year(x):
    """Find the year from the expression"""
    year = None
    try:
        return int(x.split()[-1])
    except:
        year = re.search('(?P<y>[0-9]{3,4})', x)
        year = 3000 if not year else int(year.group('y'))
    return  year


def parse_calendar_files(d):
    events = {}
    rx = re.compile('^[0-9]+\/[0-9]+')
    fmtint = lambda x: '{0:02d}'.format(int(re.sub('\*', '', x)))
    for filename in glob.glob(join(d, 'calendar.*')):
        itis = 0
        for line in open(filename, 'rb').readlines():
            tabbed, line = stringify(line)
            if tabbed:
                events[the_date][-1] += ' ' + line
            elif rx.search(line):
                xx, event = split1(line)
                the_date = '/'.join(fmtint(x) for x in xx.split('/'))
                events.setdefault(the_date, []).append(event)
                if 'Cygnus' in event:
                    itis = 1
    return events


def dump_cal(cal):
    def month_day(day):
        month, day = [int(x) for x in day.strip(':').split('/')]
        return (month, day)
    fh = open(my_calendar_file, 'w')
    dates = sorted(cal.keys(), key=lambda x: month_day(x))
    for date in dates:
        list_of_events = cal[date]
        for event in list_of_events:
            fh.write('{0}: {1}\n'.format(date, event))
    fh.close()


def load_cal():
    if not isfile(my_calendar_file):
        d = '/usr/share/calendar'
        if not isdir(d):
            sys.exit(0)
        events = parse_calendar_files(d)
        dump_cal(events)
        return events
    cal = {}
    for line in open(my_calendar_file):
        if not line.split():
            continue
        line = line.split(':', 1)
        cal.setdefault(line[0].strip(), []).append(line[1].strip())
    return cal


def print_the_days_events(day):
    events = load_cal()
    events_of_day = events.get(day)
    if events_of_day is None:
        return 0

    events_of_day = sorted(events_of_day, key=lambda x: find_year(x))
    sys.stderr.write("""{3}
  ______          __               _          __  ___      __
 /_  __/___  ____/ /___ ___  __   (_)___     / / / (_)____/ /_____  _______  __
  / / / __ \/ __  / __ `/ / / /  / / __ \   / /_/ / / ___/ __/ __ \/ ___/ / / /
 / / / /_/ / /_/ / /_/ / /_/ /  / / / / /  / __  / (__  ) /_/ /_/ / /  / /_/ /
/_/  \____/\__,_/\__,_/\__, /  /_/_/ /_/  /_/ /_/_/____/\__/\____/_/   \__, /
                      /____/                                          /____/
\n{0} {1} {2}\n{3}\n""".format('-'*3, time.strftime('%b %d'), '-'*69, '='*80))

    for event in events_of_day:
        try:
            sys.stderr.write(event+'\n')
        except:
            continue

    return 0

if __name__ == '__main__':
    sys.exit(main())
