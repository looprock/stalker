About:

I wrote stalker.py based on the inspiration from the stalk and collect scripts from aspsersa (https://code.google.com/p/aspersa/). I liked the concept, but I wanted something I could run via cron across all servers so I could capture their states when they had issues without having to anticpate when that would be. stalker.py maintains an sqlite database for data persistence between runs, and once an issue exceeds max_alarms, a collection is triggered. 

I've included toggles for a cpu threshold, free memory threshold, and a mysql threads threshold that can all be enabled and disabled via the config, /etc/stalker/stalker.cnf. 

/etc/stalker/stalker.cnf looks something like this:

[default]
# Error notification mail settings
# your smtp server
mailhost = "localhost"
# who the mail is addressed from
mailfrom = "stalker@yourcompany.com"
# address notifications get sent to
mailto = "ops@yourcompany.com"
# mem_timeout, cpu_timeout and mysql_timeout all inherit this value if not specified:
timeout = "10"
max_alarms = "3"
cpu_stalk = "T"
# if you don't set cpu_high, the script will use .75 x the number of processors in the system as the high water mark
#cpu_high = "1.0"
mem_stalk = "T"
mem_free_low_percent = "20"
mysql_stalk = "F"
mysql_timeout = "15"
mysql_admin = "/usr/bin/mysqladmin"
mysql_args = ""
mysql_max_threads = "200"
collector_timeout = "60"
# an excellent collector can be found at: https://code.google.com/p/aspersa/
collector = "/usr/local/bin/collector 1 1"

The database is stored under /var/lib/stalker/stalker.db, which will get created at first run.

I've also included a basic collector script which includes data from:
top
netstat
vmstat
mpstat
sar
ps
free
iostat
sysctl
lsof

For the mysql inclined, a much better one can be found if you download the aspersa git repo.
