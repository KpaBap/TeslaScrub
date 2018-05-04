  _______        _        _____                 _
 |__   __|      | |      / ____|               | |
    | | ___  ___| | __ _| (___   ___ _ __ _   _| |__
    | |/ _ \/ __| |/ _` |\___ \ / __| '__| | | | '_ \
    | |  __/\__ \ | (_| |____) | (__| |  | |_| | |_) |
    |_|\___||___/_|\__,_|_____/ \___|_|   \__,_|_.__/

Checks if your Tesla profile has changed from a reservation number to something else

-- Python 3.6 or later required

Run:

```
pip install -r requirements.txt
```

Edit config.ini and put in all the required settings
BORING_EMAIL_FREQUENCY is how often to send an email even if nothing has changed - lets you know the script is still working
CRONJOB_FREQUENCY tells the script how often it's scheduled to run, to prevent sending emails too often

There will be a log file called 'teslascrub.log' in the same directory as the script.
Setting DEBUG to 'yes' may end up logging some private information in the log file. SANITIZE BEFORE SHARING!

Schedule a cron job or task to run the script - for example every 10 minutes:

```
*/10 * * * * python teslascrub.py
```



