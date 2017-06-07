###Description

It's small telegram bot that takes updates from Redmine database 
and posts messages about new issues to Telegram chat.

To start using:

* Clone the repository
* Rename config_template.py to config.py and enter your account data
* Make sure that Redis is up and running on your host, change the port if necessary
* Add 'python main.py' to cron with the frequency you need to check and report the updates.
