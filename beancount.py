#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Yue Wu
# @Date:   2016-02-29 23:43:43
# @Last Modified by:   Yue Wu
# @Last Modified time: 2016-03-02 18:25:57

import re
import sys
import json
from math import log
from datetime import datetime


class beancount:

    '''APPEND OR MODIFY BEANCOUNT ENTRY WITH ALFRED:

    bean_add: add new entry to beancount file;
    bean_clear: clear an entry in beancount file by adding #clear tag;
    bean_cache: create a cache file with all accounts and payees with frequency.
    '''

    def __init__(self, wf, settingpath='beancount.json'):
        self.wf = wf
        self.length = len(wf.args)-1
        self.args = wf.args[1:] + ['']*(6-self.length)
        with open(settingpath, 'r') as settingfile:
            self.settings = json.loads(settingfile.read())

    def bean_add(self):
        try:
            with open(self.settings['temp_path'], 'r') as tempfile:
                accounts = json.loads(tempfile.read())
        except IOError:
            accounts = self.bean_cache()

        subtitle = u'{from} ➟ {to} by {payee}'
        params = ['from', 'to', 'payee'][:self.length]
        values = {x: '\t' for x in ['from', 'to', 'payee']}

        for index, p in enumerate(params[:self.length-1]):
            values[p] = self.rank(self.args[index], accounts[p])[0][0]

        if self.length <= 3:
            for v, _ in self.rank(self.args[self.length-1], accounts[params[-1]]):
                values[params[-1]] = v
                self.wf.add_item(v, subtitle.format(**values), valid=False)
        else:
            values['date'] = datetime.now().strftime('%Y-%m-%d')
            values['amount'] = float(self.args[3])
            values['comment'] = self.args[4]
            values['tags'] = self.args[5]
            entry = [self.settings['title_format'].format(**values).strip()]
            entry.append(self.settings['body_format'].format(
                account=values['from'], flow=-values['amount'],
                currency=self.settings['default_currency']
            ))
            entry.append(self.settings['body_format'].format(
                account=values['to'], flow=values['amount'],
                currency=self.settings['default_currency']
            ))
            entry = '\n'.join(entry)
            self.wf.add_item(
                title='New ${amount:.2f} Entry'.format(**values),
                subtitle=subtitle.format(**values),
                valid=True,
                arg=entry,
                copytext=entry
            )

    def bean_cache(self, ledger_path=None):
        if not ledger_path:
            ledger_path = self.settings['ledger_path']
        with open(ledger_path, 'r') as beanfile:
            bean = beanfile.read()

        matches = {}
        for key, reg in self.settings['regexes'].items():
            pattern = re.compile(reg)
            matches[key] = pattern.findall(bean)

        accounts = {
            'from': {
                x: matches['from'].count(x)
                for x in matches['open']
                if x not in matches['close']
            },
            'to': {
                x: matches['to'].count(x)
                for x in matches['open']
                if x not in matches['close']
            },
            'payee': {
                x: matches['payee'].count(x)
                for x in set(matches['payee'])
            }
        }

        with open(self.settings['temp_path'], 'w') as tempfile:
            json.dump(accounts, tempfile)

        return accounts

    def bean_clear(self):
        pass

    def rank(self, inputs, searches):
        results = self.wf.filter(inputs, searches.keys(), include_score=True)
        results = [(v, s*log(searches[v]+1))
                   for v, s, _ in results]+[(inputs, 0)]
        return sorted(results, key=lambda x: -x[1])


def main(wf):
    bean = beancount(wf)
    action = wf.args[0]
    if action == 'add':
        bean.bean_add()
    elif action == 'cache':
        if len(wf.args) >= 2:
            ledger_path = wf.args[1]
        else:
            ledger_path = None
        bean.bean_cache(ledger_path)
    elif action == 'clear':
        bean.bean_clear()

    wf.send_feedback()


if __name__ == '__main__':
    from workflow import Workflow

    update_settings = {
        'github_slug': 'username/reponame',
        'version': '0.0.1',
        'frequency': 7
    }

    wf = Workflow()
    wf.magic_prefix = 'wf:'
    sys.exit(wf.run(main))
