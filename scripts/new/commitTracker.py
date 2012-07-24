#!/usr/bin/env python

# Commit tracker


import argparse
from ConfigParser import SafeConfigParser
import os
import re
from subprocess import Popen,PIPE,check_call
import sys
import time

class Config(object):
    def __init__(self):
        self.set_defaults()
        self.parse_args()
        self.read_config()
        self.set_config()

    def set_defaults(self):
        home = os.getenv('HOME')
        now = time.localtime()
        if home:
            # configuration file
            self.config_file = home + os.sep + '.committrackerrc'
            # repository
            self.repository_root = home + os.sep + 'WebKit'
        else:
            self.config_file = None
            self.repository_root = None
        self.verbose = False
        # should we fetch the latest?
        self.do_fetch = True
        # Date to start grabbing commits at.
        self.since = '01/01/{0}'.format(now.tm_year)
        # This should be set in the config file in the "People" section!
        # dictionary of people who's contributions we are looking for
        # name -> email address
        self.people = { }

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Count commits by the Adobe Web Platform Team')
        parser.add_argument('--config', default=None, help='Path to config file, default is {0}'.format(self.config_file))
        parser.add_argument('--verbose', action='store_true', help='Turn on verbose mode')
        parser.add_argument('--no-fetch', dest='no_fetch', action='store_true', help="Don't fetch from origin before counting")
        parser.add_argument('--since', default=None, help='Start date for counting. Defaults to Jan 1st of the current year.')
        parser.add_argument('--repo', dest='repository_root', default=None, help='Path to WebKit git repository')
        self.args = parser.parse_args()

    def read_config(self):
        self.file = SafeConfigParser(allow_no_value=True)
        if self.args.config:
            self.config_file = self.args.config
            with open(self.config_file) as fp:
                self.file.readfp(fp, self.config_file)
        else:
            self.file.read(self.config_file)

    def set_config(self):
        if self.args.verbose:
            self.verbose = True
        elif self.file.has_option('Options', 'verbose'):
            self.verbose = self.file.get_boolean('Options', 'verbose')

        if self.args.no_fetch:
            self.do_fetch = False
        elif self.file.has_option('Options', 'do_fetch'):
            self.do_fetch = self.file.get_boolean('Options', 'do_fetch')

        if self.args.since:
            self.since = self.args.since
        elif self.file.has_option('Options', 'since'):
            self.since = self.file.get('Options', 'since')

        if self.args.repository_root:
            self.repository_root = self.args.repostitory_root
        elif self.file.has_option('Options', 'repository_root'):
            self.repository_root = self.file.get('Options', 'repository_root')

        if self.file.has_section('People'):
            self.people = { person[0] : person[1] for person in self.file.items('People') }

        # This is case insensitive because ConfigParser throws away the case of all of it's keys.
        self.people_matcher = re.compile(self.people_regexp(), re.IGNORECASE)

    def people_regexp(self):
        def helper(l):
            return '|'.join([ re.escape(i) for i in l if len(i) > 0 ])
        return helper(self.people.keys()) + '|' + helper(self.people.values())


class Counter(object):
    def __init__(self, data, config):
        self.data = data
        self.count = 0
        self._config = config

    def start(self):
        self._next_commit()
        for line in self.data:
            if line.startswith('Author'):
                if self._line_has_person(line):
                    if self._config.verbose:
                        print line
                    self.count += 1
                    self._next_commit()
            elif line.strip().startswith('Patch by'):
                if self._line_has_person(line):
                    if self._config.verbose:
                        print line
                    self.count += 1
                    self._next_commit()

    def _next_commit(self):
        for line in self.data:
            if line.startswith('commit'):
                if self._config.verbose:
                    print line
                return

    def _line_has_person(self, line):
        return self._config.people_matcher.search(line)

config = Config()

os.chdir(config.repository_root)

if config.do_fetch:
    print "Fetching updates"
    check_call(['git', 'fetch', 'origin'])

print "Processing log"
log = Popen(['git', 'log', 'origin/master', '--since="{0}"'.format(config.since)], stdout=PIPE)
counter = Counter(log.stdout, config)
counter.start()

print('Counted {0} commits since {1}'.format(counter.count, config.since))