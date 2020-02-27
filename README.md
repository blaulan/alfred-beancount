Alfred workflow to modify beancount file with account/payee auto-complete. Thanks to [beancount](http://furius.ca/beancount/), [Alfred-Workflow](http://www.deanishe.net/alfred-workflow/) and [iconmonstr](http://iconmonstr.com/). Please remember to modify the corresponding regex in `beancount.json` to match your entry format.

### Instruction for 1st Run

Download the workflow from [latest release](https://github.com/blaulan/alfred-beancount/releases/latest). You will need to change `ledger_path` in workflow environment variables. The regexes in `beancount.json` will catch histrorical transactions correctly most time. However, if anything went wrong, modify them to match your file may solve the problem. Output of `bean-add` function is defined by `title_format` and `body_format`, if you want different format, that's where you should refer to. 

Python 2 is required and the executable path is defined in the `python_path` variable. You will also need to install the dependencies described in `requirements.txt` with the following command:

> pip2 install -r requirements.txt

### Append a new entry to existing beancount file

> bean-add FROM_ACCOUNT TO_ACCOUNT '[PAYEE]' AMOUNT '[TAGS]' '[COMMENT]'

Workflow will list all the possible outcomes for the last parameter, while using the best fit for the rest. For example, if user input is `bean-add Slate RES`, the best match for `FROM_ACCOUNT` is `Liabilities:US:Chase:Slate`, so the program will use that account as fund source. Meanwhile, all the possible matches for `RES` will be listed out. 

![bean-add](/screenshots/bean-add.png?raw=true)

### Rebuild account and payee caches

> bean-cache [PATH_TO_BEANCOUNT_FILE]

### Clear an transaction by adding #clear tag

> bean-clear [FROM_ACCOUNT]

![bean-clear](/screenshots/bean-clear.png?raw=true)
