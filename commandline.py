# -*- coding: utf-8 -*-
# @Author: Yue Wu <me@blaulan.com>
# @Date:   2020-02-29 17:49:05
# @Last Modified By:   Yue Wu <me@blaulan.com>
# @Last Modified Time: 2020-03-02 22:06:26

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError
from beancount import Beancount


class BeancountCompleter(Completer):
    def set_bean(self, bean):
        self.bean = bean

    def get_completions(self, document, complete_event):
        inputs = document.text.strip().split()
        if len(inputs)>3 or (document.text[-1]==' '):
            results = []
        else:
            results = self.bean.bean_add(inputs)
        for r in results:
            yield Completion(r['title'], start_position=0)


class BeancountValidator(Validator):
    def set_bean(self, bean):
        self.bean = bean

    def set_toolbar(self, toolbar):
        self.toolbar = toolbar

    def validate(self, document):
        inputs = document.text.strip().split()
        if not inputs:
            return
        if len(inputs)>3 and not inputs[3].replace('.','',1).isdigit():
            raise ValidationError(
                message='amount value error',
                cursor_position=len(document.text)-1
            )
        results = self.bean.bean_add(inputs)
        self.toolbar.set_text(results[0]['subtitle'])


class BeancountToolbar:
    def __init__(self):
        self.clear_text()

    def clear_text(self):
        self.text = ''

    def set_text(self, text):
        self.text = text

    def get_text(self):
        return self.text


if __name__=='__main__':
    bean = Beancount()
    toolbar = BeancountToolbar()
    completer = BeancountCompleter()
    completer.set_bean(bean)
    validator = BeancountValidator()
    validator.set_bean(bean)
    validator.set_toolbar(toolbar)
    session = PromptSession(
        completer=completer,
        complete_while_typing=True,
        validator=validator,
        validate_while_typing=True,
        bottom_toolbar=toolbar.get_text
    )

    while True:
        try:
            text = session.prompt('> ')
        except KeyboardInterrupt:
            toolbar.clear_text()
            continue
        except EOFError:
            break
        output = bean.bean_add(text.strip().split())[0]
        with open(bean.settings['default_ledger'], 'a') as ledger_file:
            ledger_file.write(output['arg']+'\n\n')
        print(output['arg'])
        toolbar.clear_text()

    print('session ended!')
