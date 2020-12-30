#!/usr/bin/python
"""For TimeWatch Version 5.069
Last updated at 30/12/2020"""

import argparse
import datetime
import logging

import timewatch


def some_func(company, username, password):

    #  parser = argparse.ArgumentParser(description='Automatic work hours reporting for timewatch.co.il')
    #
    #  parser.add_argument('company', type=int, help='Company ID')
    #  parser.add_argument('user', help='user name/id')
    #  parser.add_argument('password', help='user password')

    today = datetime.date.today()
    year = today.year
    month = today.month
    verbose = 0
    override = 'incomplete'
    # starttime = '09:00'
    # daysoff = ['friday', 'saturday']
    jitter = 10
    retries = 2


    #  parser.add_argument('-y', '--year', default=today.year, type=int, help='Year number to fill')
    #  parser.add_argument('-m', '--month', default=today.month, help='Month number or name')
    #
    #  parser.add_argument('-v', '--verbose', default=0, action='count', help='increase logging level')
    #
    #  parser.add_argument('-o', '--override', default='incomplete',
    #                      choices=['all', 'incomplete', 'regular'],
    #                      help='Control override behavior. all - override all '
    #                           'working days, unsafe to vacation/sick days. '
    #                           'incomplete = only override days with partial '
    #                           'records. regular - override regular days '
    #                           '(without absence reason) only')
    #
    #  parser.add_argument('-s', '--starttime', default='09:00', help='punch-in time')
    #  parser.add_argument('-d', '--daysoff', default=['friday', 'saturday'], help='''Days you're off, not working,
    # the defaults are Friday and Saturday''')
    #
    #  parser.add_argument('-j', '--jitter', default=10, type=int,
    #                      help='punching time random range in minutes.')
    #
    #  parser.add_argument('-r', '--retries', default=9, help='amount of times to retries on failed punchin')
    #
    #  args = parser.parse_args()

    verbosity_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    verbosity = min(verbose, len(verbosity_levels) - 1)
    logging_level = verbosity_levels[verbosity]

    tw = timewatch.TimeWatch(logging_level)
    # loglevel=logging_level,
    # override=args.override,
    # starttime=args.starttime,
    # jitter=args.jitter,
    # retries=args.retries,
    # daysoff=args.daysoff)

    # login = tw.login(args.company, args.user, args.password)

    login = tw.login(company, username, password)
    if login == "Login failed!":
        return "Login failed! - Double check your user/password and re-run the bot"
    else:
        text = tw.edit_month(year, month)
        print(text)
        return text
