# -*- coding: utf-8 -*-

import os
import re
import sys
import math
import glob
import json
from datetime import datetime
from pypinyin import lazy_pinyin
from rapidfuzz import fuzz, process


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

        # setup variables
        self.accounts = []

    def bean_add(self, inputs):
        if not self.accounts:
            try:
                with open(self.settings['cache_path'], 'r') as tempfile:
                    self.accounts = json.loads(tempfile.read())
            except IOError:
                self.accounts = self.bean_cache()

        params = ['from', 'to', 'payee', 'amount', 'tags', 'comment']
        values = {p: 0 if p=='amount' else '' for p in params}
        for p,v in zip(params, inputs):
            # handle matches for accounts
            if p in params[:3]:
                # param start with exclamation mark will be returned exactly
                # otherwise it will be matched against existing accounts
                if v[0]=='!':
                    matches = [v[1:].replace('_', ' ')]
                else:
                    matches = self.rank(v.replace('_', ' '), self.accounts[p])
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
                            if m in self.accounts['mapping']:
                                account = self.accounts['mapping'][m]
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
                    if p=='payee' and account in self.accounts['mapping']:
                        account = self.accounts['mapping'][account]
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
        cache_files = []
        if 'cache_files' in self.settings:
            cache_files = [os.path.join(ledger_folder, f) for f in self.settings['cache_files']]
        else:
            cache_files = glob.glob(os.path.join(ledger_folder, '*.beancount'))
        for f in cache_files:
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
            'payee': {k:v for k,v in {
                self.decode(x): matches['payee'].count(x)
                for x in set(matches['payee'])
            }.items() if v>1},
            'mapping': {
                self.decode(x): x
                for x in set(matches['payee'])
            }
        }

        with open(self.settings['cache_path'], 'w') as tempfile:
            json.dump(accounts, tempfile)
        return accounts

    def rank(self, target, searches, limit=10):
        target = target.replace('\'', '').replace('"', '')
        if not target:
            return ['']
        matches = process.extract(
            target, searches.keys(), limit=limit, scorer=fuzz.partial_ratio)
        matches = [(m[0], m[1]*math.log(searches[m[0]]+1)) for m in matches if m[1]>60]
        if matches:
            return [m[0] for m in sorted(matches, key=lambda d: -d[1])]
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
