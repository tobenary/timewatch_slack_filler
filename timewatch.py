# coding=utf8
import requests
import os
import datetime
import time
import logging
import random
import re
from bs4 import BeautifulSoup as BS
from collections import defaultdict

try:
    strtypes = (str, 'UTF-8')

except:
    strtypes = str


def BeautifulSoup(t):
    return BS(t, 'html.parser')


class TimeWatchException(Exception):
    pass


class TimeWatch:
    def __init__(self, loglevel=logging.WARNING, **kwargs):
        """Assigning all pre-req fields"""
        self.site = "https://c.timewatch.co.il/"
        self.editpath = "punch/editwh3.php"
        self.loginpath = "user/validate_user.php" # https://c.timewatch.co.il/user/validate_user.php
        self.dayspath = "punch/editwh.php"

        self.offdays = ['friday', 'saturday']
        self.override = 'incomplete'
        self.jitter = 20
        self.starttime = '09:00'
        self.duration = '9:35'
        self.retries = 5
        self.config = ['offdays', 'override', 'jitter', 'starttime', 'duration', 'retries']

        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(loglevel)

        self.loggedin = False
        self.session = requests.Session()

        self.set_config(**kwargs)

    def set_config(self, **kws):
        for key, value in kws.items():
            if key not in self.config:
                self.logger.warning("Skipping parameter not listed in config: {}".format(key))

            if hasattr(self, "set_" + key):
                getattr(self, "set_" + key)(value)
            else:
                setattr(self, key, value)

            self.logger.debug("Set {} = '{}'".format(key, value))

    def post(self, path, data, headers=None):
        return self.session.post(os.path.join(self.site, path), data, headers)

    def get(self, path, data):
        return self.session.get(os.path.join(self.site, path), params=data)

    def login(self, company, user, password):
        """Company - company number is filled by user when logging in
        user - id/employee number as filled by user when logging in
        password - password as filled by user when logging in
        employeeid - id as internally represented by website after successful login"""
        data = {'comp': company, 'name': user, 'pw': password}
        r = self.post(self.loginpath, data, headers=None)
        if not ("שלום" and "התנתק" ) in r.text:  # if "The login details you entered are incorrect!" in r.text:
            # raise TimeWatchException("Login failed!")
            return "Login failed!"
        csrf_token = re.search(r'hidden name=csrf_token value="(.*)"', r.text)
        self.loggedin = True
        self.company = company
        self.user = user
        self.password = password
        self.employeeid = int(BeautifulSoup(r.text).find('input', id='ixemplee').get('value'))
        self.logger.info("successfully logged in as {} with id {}".format(self.user, self.employeeid))
        self.csrf_token = csrf_token.group(1)
        return r

    def time_to_tuple(self, t):
        """Return time in tuple"""
        if isinstance(t, strtypes):
            t = self.clean_text(t)
            if ':' in t:
                t = list(map(int, t.split(':')))
            else:
                t = ('', '')
        if isinstance(t, list):
            t = tuple(t)

        if not isinstance(t, tuple) or not len(t) == 2:
            raise Exception("couldn't convert time to tuple: {}".format(t))

        return t

    def tuple_to_str(self, t):
        """Return string from tuple"""
        return ':'.join(map(str, t))

    def edit_date(self, year, month, date, date_duration):
        """Edit a date based on the chosen method.
        The output of this function will be sent to the "edit_date_post" function"""
        end1 = end2 = None
        start1 = start2 = None
        start = self.starttime
        start = self.time_to_tuple(start)
        jitter = random.randint(1, self.jitter)
        current_date_duration_hour = date_duration[date][0][0]
        current_date_duration_min = date_duration[date][0][1]
        if isinstance(current_date_duration_hour, str):  # if there is no punch at att, set the var to 100
            current_date_duration_hour = 100
            current_date_duration_min = 100

        # Scenario 1: The duration is above 9+ hours, no need to update
        if 9 <= current_date_duration_hour < 100 and 0 <= \
                current_date_duration_min <= 59:
            if 10 == current_date_duration_hour and 0 <= \
                    current_date_duration_min <= 59:
                return None  # No need to punch, already beyond 9.x hours
            else:
                return None  # No need to punch, already beyond 9.x hours

        # Scenario 2: The duration is below 9 hours, and only one punch at the BEGINNING of the day, we need to update2.
        elif date_duration[date][2] == 'punched_no_change' and date_duration[date][4] == 'none':
            start = date_duration[date][1][0], date_duration[date][1][1]
            end = date_duration[date][1][0] + 9, (date_duration[date][1][1] + jitter)  # setting random end value
            if end[1] > 59:
                end = end[0] + 1, end[1] % 60  # If the minutes were more than 59, we need to add an hour.
            what_to_punch = 12  # punch in position 2. Only position 1 was punched.

        # Scenario 3: The duration is below 9 hours, and only one punch at the END of the day, we need to update1.
        elif date_duration[date][4] == 'punched_no_change' and date_duration[date][2] == 'none':
            # Calculating how many hours we need
            delta1 = datetime.timedelta(hours=9, minutes=5 + jitter)
            delta2 = datetime.timedelta(hours=date_duration[date][3][0], minutes=date_duration[date][3][1])
            how_many_left = delta2 - delta1
            hour_start = int(how_many_left.seconds / 3600)
            minutes_start = int((how_many_left.seconds / 60) % 60)
            start = hour_start, minutes_start
            end = date_duration[date][3][0], date_duration[date][3][1]
            what_to_punch = 12  # punch in position 1. Only position 2 was punched.

        # Scenario 4: The duration is below 9 hours, but two punches were made.
        elif date_duration[date][2] and date_duration[date][4] == 'punched_no_change' and date_duration[date][0][0] < 9:
            if date_duration[date][1][0] > 9:
                # Calculating how many hours we need
                delta1 = datetime.timedelta(hours=9, minutes=5 + jitter)
                delta2 = datetime.timedelta(hours=date_duration[date][0][0], minutes=date_duration[date][0][1])
                how_many_left = delta1 - delta2
                punch = how_many_left + \
                        datetime.timedelta(hours=date_duration[date][3][0], minutes=date_duration[date][3][1])
                hour_end = int(punch.seconds / 3600)
                minutes_end = int((punch.seconds / 60) % 60)

                what_to_punch = 1234  # punch in position 1,2,3,4
                start = date_duration[date][1][0], date_duration[date][1][1]
                end = date_duration[date][3][0], date_duration[date][3][1]
                if date_duration[date][3][1] == 59:
                    start1 = date_duration[date][3][0] + 1, 0  # edge case where time ends with :59
                else:
                    start1 = date_duration[date][3][0], date_duration[date][3][1] + 1
                end1 = hour_end, minutes_end

        # Scenario 5: not punched at all.
        else:  # Normal cases, not coming to the office, need to punch entry and exit.
            what_to_punch = 12  # punch in position 1 and 2
            # The below is when someone decided to "hand do" an entry.
            if isinstance(date_duration[date][1][0], int):
                start = date_duration[date][1][0], date_duration[date][1][1]
                end = start[0] + 9, start[1] + jitter
                if end[1] > 59:
                    end = end[0] + 1, end[1] % 60
            else:
                start = 9, 0 + jitter
                end = 18, 5 + jitter
        failures = 0
        while not (
                self.edit_date_post(date, year, month, start, end, what_to_punch,
                                    start1, end1, start2, end2)
                and self.validate_date(year, month, date, start, end, what_to_punch)):
            failures += 1
            if failures >= self.retries:
                self.logger.warning('Failed punching in {} times on {}'.format(failures, date))
                return False
        return True

    def edit_date_post(self, date, year, month, start=None, end=None,
                       what_to_punch=None, start1=None, end1=None, start2=None,
                       end2=None):
        """The actual process of "punching" / editing the page with the new data from the step before."""
        date_str = '{y}-{m}-{d}'.format(y=date.year, m=date.month, d=date.day)
        data = {'e': str(self.employeeid), 'tl': str(self.employeeid), 'c': str(self.company), 'd': str(date),
                'nextdate': '', 'csrf_token': self.csrf_token
                }
        start_hour, start_minute = start
        end_hour, end_minute = end

        if what_to_punch == 3456 or what_to_punch == 1234:
            # Updating the first position.
            data.update(
                {'task0': '0', 'taskdescr0': '', 'what0': '1', 'emm0': str(start_minute), 'ehh0': str(start_hour),
                 'xmm0': str(end_minute), 'xhh0': str(end_hour)})  # Update 1,2
            # Updating the 2nd position.
            start_hour, start_minute = start1
            end_hour, end_minute = end1
            data.update(
                {'task1': '0', 'taskdescr1': '', 'what1': '1', 'emm1': str(start_minute), 'ehh1': str(start_hour),
                 'xmm1': str(end_minute), 'xhh1': str(end_hour)})  # Update 3,4
            # if what_to_punch == 3456:
            #     start_hour, start_minute = start2
            #     end_hour, end_minute = end2
            #     data.update(
            #         {'task2': '0', 'taskdescr2': '', 'what2': '1', 'emm2': str(start_minute), 'ehh2': str(start_hour),
            #          'xmm2': str(end_minute), 'xhh2': str(end_hour)})  # Update 5,6
        elif what_to_punch == 34:
            data.update(
                {'task1': '0', 'taskdescr1': '', 'what1': '1', 'emm1': str(start_minute), 'ehh1': str(start_hour),
                 'xmm1': str(end_minute), 'xhh1': str(end_hour)})
        else:
            data.update(
                {'task0': '0', 'taskdescr0': '', 'what0': '1', 'emm0': str(start_minute), 'ehh0': str(start_hour),
                 'xmm0': str(end_minute), 'xhh0': str(end_hour)})

        self.session.headers = {
            'Content-Type': r"application/x-www-form-urlencoded; charset=UTF-8",
            'Referer': f"https://c.timewatch.co.il/punch/editwh.php?month="
                       f"{month}&year={year}&teamldr={self.employeeid}&empl_name={self.company}"
            }
            # 'Referer': r"https://c.timewatch.co.il/punch/editwh2.php?ie={"
            #            r"0}&e={1}&d={2}&jd={2}&tl={1}".format(
            #     self.company, self.employeeid, date)
        # }
        r = self.post(self.editpath, data, self.session.headers)

        if "TimeWatch - Reject" in r.text or "error " in r.text or u"אינך" in r.text:
            print("error")
            self.logger.info('Failure punching in on {} as {} to {}'.format(date_str, self.tuple_to_str(start),
                                                                            self.tuple_to_str(end)))
            return False

        self.logger.info(
            'Punched in on {} as {} to {}'.format(date_str, self.tuple_to_str(start), self.tuple_to_str(end)))
        return True

    def clean_text(self, text):
        return text.strip().replace("&nbsp;", "")

    def parse_dates(self, year, month, keep_cause):
        """Which dates to work on, it gets the weekdays which has working day or Thursday in the right tab.
        Then, it process them into the next function.
        punchclock4.jpg and internet4.jpg = real punch with the tag or from the internet, cannot be changed!
        oved4.png - May be changed.
        The output will be as follows:
        {current duration}, {first entry}, {what punched it? ( or none )} , {second entry},{what punched it? ( or none )},
        ..., same for 3 and 4... """
        data = {'ee': self.employeeid, 'e': self.company, 'y': year, 'm': month}
        r = self.get(self.dayspath, data)

        dates = set()
        date_durations = defaultdict(list)
        for tr in BeautifulSoup(r.text).findAll('tr', attrs={'class': 'update-data'}):
            tds = tr.findAll('td')
            date = datetime.datetime.strptime(tds[0].getText().split(" ")[0], "%d-%m-%Y").date()
            cause = True if self.clean_text(tds[10].getText()) else False
            working_day = True if self.clean_text(tds[2].getText()) == u"יום עבודה" or self.clean_text(
                tds[2].getText()) == u"חמישי" else False
            if keep_cause is False or cause is False and working_day is True:
                dates.add(date)
                date_durations[date].append(self.time_to_tuple(tds[12].getText()))  # get current duration
                for i in range(4, 8):  # Get entries and punches
                    date_durations[date].append(self.time_to_tuple(tds[i].getText()))
                    if len(tds[i].contents[0].contents) == 2:  # Check if it's not empty. reducing faults.
                        if tds[i].contents[0].contents[1] is not None:
                            if tds[i].contents[0].contents[1].attrs['src'] == '/images/punchclock4.jpg':
                                date_durations[date].append('punched_no_change')
                            elif tds[i].contents[0].contents[1].attrs['src'] == '/images/oved4.png':
                                date_durations[date].append('hand')
                            elif tds[i].contents[0].contents[1].attrs['src'] == '/images/internet4.jpg':
                                date_durations[date].append('punched_no_change')
                    elif tds[i].contents[0].text.strip() == '':
                        date_durations[date].append('none')
                    else:
                        pass  # this is an unknown state
                        self.logger.debug('parsed expected duration for {} as {}'.format(date, date_durations))
        return dates, date_durations

    def validate_date(self, year, month, expected_date, expected_start, expected_end, what_to_punch):
        data = {'teamldr': self.employeeid, 'empl_name': self.company, 'year': year,
                'month': month}
        retry = True
        while retry:
            r = self.get(self.dayspath, data)
            if str(expected_date) not in r.text:
                time.sleep(random.randint(1, 3))
            else:
                retry = False

        for tr in BeautifulSoup(r.text).findAll('tr', attrs={'class': 'update-data'}):
            tds = tr.findAll('td')
            date = datetime.datetime.strptime(tds[0].getText().split(" ")[0], "%d-%m-%Y").date()
            if date != expected_date:
                continue
            if what_to_punch == 12 or what_to_punch == 1234:
                i = 4
            elif what_to_punch == 34:
                i = 6
            elif what_to_punch == 3456:
                return True
            start = self.time_to_tuple(tds[i].getText())
            end = self.time_to_tuple(tds[i + 1].getText())
            if start != expected_start or end != expected_end:
                self.logger.info(
                    'Validation failed, expected: {} - {}. read: {} - {}'.format(expected_start, expected_end, start,
                                                                                 end))
                return False

            self.logger.debug('Successful validation for {} as {}-{}'.format(expected_date, start, end))
            return True

        self.logger.info('Validation failed reading punch time for {}'.format(expected_date))
        return False

    def month_number(self, month):
        if isinstance(month, int):
            return month

        if isinstance(month, strtypes) and month.isdigit():
            return int(month)

        for fmt in ['%b', '%B']:
            return time.strptime(month, fmt).tm_mon

        raise ValueError("Invalid month input: {}".format(month))

    def edit_month(self, year, month):
        month = self.month_number(month)
        print(f"the month is {month}")
        print(f" the override set to {self.override}")

        if self.override == 'all':
            # in override=all mode, make sure all times are cleaned
            self.override_all = True
            self.keep_cause = False
            self.default_duration = None
        elif self.override == 'incomplete':
            # in override=incomplete mode, only override incomplete data
            # so simply clear dates without expected time
            self.override_all = False
            self.keep_cause = True
            self.default_duration = '9:05'
        elif self.override == 'regular':
            self.override_all = True
            self.keep_cause = True
            self.default_duration = None

        self.logger.info('parsing dates to operate on')
        dates, date_durations = (self.parse_dates(year, month, self.keep_cause))
        dates = sorted(dates)

        # if self.override_all:
        #     self.logger.info('overwriting all entries to retrieve expected durations')
        #     for date in tqdm(dates):
        #         self.edit_date(year, month, date, headers=None)

            # self.logger.info('parsing expected durations')
            # date_durations = self.parse_expected_durations(year, month)

            # self.logger.info('punching in')

        # for date in tqdm(dates):
        for date in dates:
            done = self.edit_date(year, month, date, date_durations)
            if not done:
                print(f"\nNo need punching for {date}, moving on...")
            elif done:
                print(f"\nDone punching for {date}, moving on...")
        return """Timewatch site updated - Check your times!
        *MANDATORY* - login to <https://c.timewatch.co.il/punch/punch.php|timewatch_site> and check me."""