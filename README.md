Alfred workflow to modify beancount file with account/payee auto-complete. Thanks to [beancount](http://furius.ca/beancount/), [Alfred-Workflow](http://www.deanishe.net/alfred-workflow/) and [iconmonstr](http://iconmonstr.com/). Please remember to modify the corresponding regex in `beancount.json` to match your entry format.

### Append a new entry to existing beancount file

> bean-add FROM_ACCOUNT TO_ACCOUNT '[PAYEE]' AMOUNT '[TAGS]' '[COMMENT]'

Workflow will list all the possible outcomes for the last parameter, while using the best fit for the rest. For example, if user input is `bean-add Slate RES`, the best match for `FROM_ACCOUNT` is `Liabilities:US:Chase:Slate`, so the program will use that account as fund source. Meanwhile, all the possible matches for `RES` will be listed out. 

![bean-add](/screenshots/bean-add.png?raw=true)

### Rebuild account and payee caches

> bean-cache [PATH_TO_BEANCOUNT_FILE]

### Clear an transaction by adding #clear tag

> bean-clear [FROM_ACCOUNT]

![bean-clear](/screenshots/bean-clear.png?raw=true)
