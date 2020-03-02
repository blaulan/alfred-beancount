# -*- coding: utf-8 -*-
# @Author: Yue Wu <me@blaulan.com>
# @Date:   2020-02-28 16:48:17
# @Last Modified By:   Yue Wu <me@blaulan.com>
# @Last Modified Time: 2020-03-02 22:13:18

import os
import re
import sys
import glob
import json
from datetime import datetime
from fuzzywuzzy import process
from pypinyin import lazy_pinyin


class Beancount:

    """
    APPEND OR MODIFY BEANCOUNT ENTRY VIA ALFRED:

    bean_add: add new entry to beancount file;
    bean_clear: clear an entry in beancount file by adding #clear tag;
    bean_cache: create a cache file with all accounts and payees with frequency.
    """

    def __init__(self, config_path='beancount.json'):
        # read settings from config file
        with open(config_path, 'r') as setting_file:
            self.settings = json.load(setting_file)

        # read variables from environment
        for v in ['default_currency', 'ledger_folder', 'default_ledger']:
            if v in os.environ:
                self.settings[v] = os.environ[v]

        # check path for icons
        for k,v in self.settings['icons'].items():
            if not os.path.isfile(v):
                self.settings['icons'][k] = './icons/{}.png'.format(k)

    def bean_add(self, inputs):
        try:
            with open(self.settings['temp_path'], 'r') as tempfile:
                accounts = json.loads(tempfile.read())
        except IOError:
            accounts = self.bean_cache()

        params = ['from', 'to', 'payee', 'amount', 'tags', 'comment']
        values = {p: '' for p in params}
        for p,v in zip(params, inputs):
            # handle matches for accounts
            if p in params[:3]:
                matches = self.rank(v, accounts[p])
                # return the full list if last param
                if p==params[len(inputs)-1]:
                    entries = []
                    for m in matches:
                        account = m
                        icon = './icon.png'
                        if p!='payee':
                            account_type = m.split(':')[0]
                            if account_type in self.settings['icons']:
                                icon = self.settings['icons'][account_type]
                        else:
                            if m in accounts['mapping']:
                                account = accounts['mapping'][m]
                        values[p] = account
                        entries.append({
                            'title': account,
                            'subtitle': self.format_desc(values),
                            'autocomplete': account,
                            'valid': False,
                            'icon': icon
                        })
                    return entries
                else:
                    account = matches[0]
                    if p=='payee' and account in accounts['mapping']:
                        account = accounts['mapping'][m]
                    values[p] = account
            # handle transaction amount
            elif p=='amount':
                values[p] = float(v)
            # handle tags
            elif p=='tags':
                values[p] = '#'+' #'.join(v.split('+'))
            # handle comment
            else:
                values[p] = v

        values['date'] = datetime.now().strftime('%Y-%m-%d')
        entry = '\n'.join([
            self.settings['title_format'].format(**values).strip(),
            self.settings['body_format'].format(
                account=values['from'], flow=-values['amount'],
                currency=self.settings['default_currency']
            ),
            self.settings['body_format'].format(
                account=values['to'], flow=values['amount'],
                currency=self.settings['default_currency']
            )
        ])
        return [{
            'title': 'New ${amount:.2f} Entry {tags}'.format(**values),
            'subtitle': self.format_desc(values),
            'valid': True,
            'arg': entry,
            'text': entry
        }]

    def bean_clear(self, inputs=None):
        with open(self.settings['default_ledger'], 'r') as beanfile:
            bean = beanfile.read()

        for m in re.finditer(self.settings['regexes']['clear'], bean):
            tail = [i.strip() for i in m.group(2).split('"') if i.strip()!='']
            values = {
                'date': m.group(1),
                'from': m.group(3).split()[0],
                'to': m.group(4).split()[0],
                'amount': abs(float(m.group(3).split()[-2])),
                'comment': tail[0].upper() if tail else 'NULL'
            }
            yield {
                'title': '${amount:.2f} with {comment}'.format(**values),
                'subtitle': u'{date} {from} ➟ {to}'.format(**values),
                'valid': True,
                'icon': self.settings['icons'][values['from'].split(':')[0]],
                'arg': str(m.start())
            }

    def bean_cache(self, ledger_folder=None):
        # default to folder in config file
        if not ledger_folder:
            ledger_folder = self.settings['ledger_folder']

        # read and join all records
        records = []
        for f in glob.glob(os.path.join(ledger_folder, '*.beancount')):
            with open(f, 'r') as beanfile:
                records.append(beanfile.read())
        content = '\n'.join(records)

        # find matches based on regexes
        matches = {}
        for key in ['open', 'close', 'payee', 'from', 'to']:
            matches[key] = re.findall(self.settings['regexes'][key], content)

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
                self.decode(x): matches['payee'].count(x)
                for x in set(matches['payee'])
            },
            'mapping': {
                self.decode(x): x
                for x in set(matches['payee'])
            }
        }

        with open(self.settings['temp_path'], 'w') as tempfile:
            json.dump(accounts, tempfile)
        return accounts

    def rank(self, target, searches, limit=10):
        matches = [m[0] for m in process.extract(
            target, searches.keys(), limit=limit) if m[1]>0]
        if matches:
            return matches
        return [target]

    def decode(self, text):
        return ''.join(lazy_pinyin(text))

    def format_desc(self, value):
        desc = []
        if value['from']:
            desc += [value['from']]
        if value['to']:
            desc += ['➟', value['to']]
        if value['payee']:
            desc += ['by', value['payee']]
        if value['amount']:
            desc += ['¥{:.2f}'.format(value['amount'])]
        return ' '.join(desc)

    def format_alfred(self, results):
        print(json.dumps({'items': list(results)}))


if __name__=='__main__':
    # exit if no argument provided
    if len(sys.argv)==1:
        sys.exit()

    bean = Beancount()
    action = sys.argv[1]
    inputs = sys.argv[2:]
    if action == 'add':
        bean.format_alfred(bean.bean_add(inputs))
    elif action == 'cache':
        bean.bean_cache(inputs)
    elif action == 'clear':
        bean.format_alfred(bean.bean_clear(inputs))
