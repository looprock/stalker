#!/usr/bin/env python
# the concept for this script was blatantly ripped off from Aspersa (http://code.google.com/p/aspersa/)
# it was written to allow it to run from cron instead of in a screen session

import os, sys, subprocess, shlex, time, re, datetime, time, signal, smtplib
if sys.version_info >= (2,5):
	import sqlite3
else:
	from pysqlite2 import dbapi2 as sqlite3
from ConfigParser import SafeConfigParser
from email.MIMEText import MIMEText


stconfig = "/etc/stalker/stalker.cnf"
if os.path.exists(stconfig):
   parser = SafeConfigParser()
   parser.read(stconfig)
else:
   print "No config file found! Please create: %s" % stconfig
   sys.exit(1)

## /etc/stalker/stalker.cnf looks something like this:
# [default]
# mailhost = "localhost"
# mailfrom = "stalker@yourcompany.com"
# mailto = "ops@yourcompany.com"
# # mem_timeout, cpu_timeout and mysql_timeout all inherit this value if not specified:
# timeout = "10"
# max_alarms = "3"
# cpu_stalk = "T"
# # if you don't set this value the script will use .75 x the number of processors in the system as the high water mark
# #cpu_high = "0.001"
# #cpu_timeout = "10"
# mem_stalk = "T"
# mem_free_low_percent = "20"
# #mem_timeout = "10"
# mysql_stalk = "F"
# mysql_admin = "/usr/bin/mysqladmin"
# mysql_args = ""
# mysql_max_threads = "200"
# collector_timeout = "60"
# # an excellent collector can be found at: https://code.google.com/p/aspersa/
# collector = "/usr/local/bin/collector 1 1"

mailhost = parser.get('default', 'mailhost').strip('"')
mailfrom = parser.get('default', 'mailfrom').strip('"')
mailto = parser.get('default', 'mailto').strip('"')

def mailalert(message, closedb='T'):
	string = "DEBUG closedb: set to %s" % (closedb)
	debug(string)
	server = smtplib.SMTP(mailhost)
	msg = MIMEText(message)
	msg["Subject"] = "stalker.py Error!"
	msg["From"] = mailfrom
	msg["To"] = mailto
	server.sendmail(mailfrom, [mailto], msg.as_string())
	server.quit()
	if closedb == 'T':
		conn.commit()
		conn.close()
	sys.exit()

libdir = "/var/lib/stalker/"
sdb = libdir + "stalker.db"
showdebug = 'F'
def_timeout = parser.get('default', 'timeout').strip('"')

def debug(string):
	if showdebug == 'T':
		print string

def spcom(timeout, command_line):
	start = datetime.datetime.now()
	process = subprocess.Popen(shlex.split(command_line), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	while process.poll() is None:
		time.sleep(0.1)
    	now = datetime.datetime.now()
    	if (now - start).seconds> timeout:
        	os.kill(process.pid, signal.SIGKILL)
        	os.waitpid(-1, os.WNOHANG)
        	return None
	out, error = process.communicate()
	return out

### These come from: /etc/stalker/stalker.cnf
max_alarms = parser.get('default', 'max_alarms').strip('"')
cpu_stalk = parser.get('default', 'cpu_stalk').strip('"')

if cpu_stalk == 'T':
	try:
		cpu_timeout = parser.get('default', 'cpu_timeout').strip('"')
	except:
		cpu_timeout = def_timeout
	try:
		test_cpu_high = parser.get('default', 'cpu_high').strip('"')
	except:
		cpuinfo = spcom(cpu_timeout, '/bin/cat /proc/cpuinfo')
		if cpuinfo == None:
			mailalert("ERROR: timeout collecting default cpu threshold!", "F")
		test_cpu_high = cpuinfo.split().count('processor') * .75
	
mem_stalk = parser.get('default', 'mem_stalk').strip('"')
if mem_stalk == 'T':
	mem_free_low_percent = parser.get('default', 'mem_free_low_percent').strip('"')
	try:
		mem_timeout = parser.get('default', 'mem_timeout').strip('"')
	except:
		mem_timeout = def_timeout
		
mysql_stalk = parser.get('default', 'mysql_stalk').strip('"')
if mysql_stalk == 'T':
	mysql_admin = parser.get('default', 'mysql_admin').strip('"')
	mysql_args = parser.get('default', 'mysql_args').strip('"')
	mysql_max_threads = parser.get('default', 'mysql_max_threads').strip('"')
	try:
		mysql_timeout = parser.get('default', 'mysql_timeout').strip('"')
	except:
		mysql_timeout = def_timeout
		

collector = parser.get('default', 'collector').strip('"')
collector_timeout = parser.get('default', 'collector_timeout').strip('"')

# if there's no DB we need to make one
# make the dir here in case it doesn't exist
if not os.path.exists(libdir):
	os.makedirs(libdir)
	
if not os.path.exists(sdb):
	conn = sqlite3.connect(sdb)
	cur = conn.cursor()
	cur.execute('CREATE TABLE stalk (test VARCHAR(8), result INT(1))')
	conn.commit()
	conn.close()

# just assume we'll need to talk to the db after this:
try:
	conn = sqlite3.connect(sdb)
except:
	message = "Unable to open database file: %s!" % (sdb)
	mailalert(message, "F")

cur = conn.cursor()

def dict_factory(cursor, row):
    d = {}
    for idx,col in enumerate(cursor.description):
        d[col[0]] = row[idx]
        
    return d

def return_query(query):
    cur.execute(query)
    results = []
    for row in cur.fetchall():
        results.append(dict_factory(cur, row))
    return results

def getstalkers():
	scount = []
	psinfo = spcom(def_timeout, 'ps -ef').split('\n')
	for x in psinfo:
		result = re.search("stalker.py", x)
		if result != None:
			string = "DEBUG STALKERS: FOUND - %s" % (x)
			debug(string)
			scount.append(x)
	tcount = len(scount)
	string = "DEBUG STALKERS: COUNT %s" % (str(tcount))
	debug(string)
	olderrs = 'F'
	old = 0
	for t in range(0,len(prev)):
		if prev[t]['test'] == 'errors':
			old = int(prev[t]['result'])
			olderrs = 'T'
			string = "DEBUG STALKERS: found previous errors entry, old set to: %s" % (str(old))
			debug(string)
	if olderrs == 'F':
		debug("DEBUG STALKERS: No previous entries for errors")
		sql = "INSERT INTO stalk VALUES ('errors',0)"
		cur.execute(sql)
	if tcount > 1:
		current = old + 1
		string = "DEBUG STALKERS: current value: %s" % (str(current))
		# there are multiple stalker.py processes running and we've exceeded max_alerts
		if current > int(max_alarms):
			sql = "UPDATE stalk set result=%s where test='%s'" % (0, 'errors')
			cur.execute(sql)
			string = "ERROR STALKERS: too many stalker processes running over %s counts!" % (str(max_alarms))
			mailalert(string)
		else:
			# there are multiple stalker.py processes running but we haven't exceeded max_alerts
			sql = "UPDATE stalk set result=%s where test='%s'" % (current, 'errors')
			cur.execute(sql)
			conn.commit()
			conn.close()
			sys.exit()
	else:
		# no other stalker.py processes are running
		sql = "UPDATE stalk set result=%s where test='%s'" % (0, 'errors')
		cur.execute(sql)
		string = "DEBUG STALKERS: %s" % (sql)
		debug(string)

# read in the previous db contents to see if there are errors
prev = return_query("select * from stalk")

# make sure there aren't more stalker processes running, if so, check for max_alarms, then alert
getstalkers()

def getcpu():
	uptime = spcom(cpu_timeout, '/usr/bin/uptime').split()
	if uptime == None:
		mailalert("ERROR CPU: timeout collecting cpu info!")
	loadavg  = float(uptime[-3:][:1][0][:-1])
	debug("DEBUG CPU: is %s >= %s?" % (str(loadavg), str(test_cpu_high)))
	if float(loadavg) >= float(test_cpu_high):
		debug("DEBUG CPU: Yes! returning 1.")
		return 1
	else:
		debug("DEBUG CPU: NO! returning 0.")
		return 0

def getmem():
	meminfo = spcom(mem_timeout, '/bin/cat /proc/meminfo').split('\n')
	if meminfo == None:
		mailalert("ERROR: timeout collecting meminfo!")
	memfreeavail = int(meminfo[1].split()[1]) * 100 / int(meminfo[0].split()[1])
	debug("DEBUG MEM: is %s percent <= %s percent?" % (str(memfreeavail), str(mem_free_low_percent)))
	if float(memfreeavail) <= float(mem_free_low_percent):
		debug("DEBUG MEM: Yes! returning 1.")
		return 1
	else:
		debug("DEBUG MEM: NO! returning 0.")
		return 0
		
def getmysql():
	if mysql_args != "":
		mysqladmin = "%s ext %s" % (mysql_admin, mysql_args)
	else:
		mysqladmin = "%s ext" % (mysql_admin)
	mysqlinfo = spcom(mysql_timeout, mysqladmin).split('\n')
	t = "NULL"
	for x in mysqlinfo:
		result = re.search("Threads_connected", x)
		if result != None:
			t = x.split()[3]
	if t == "NULL":
		mailalert('ERROR: failed to retrieve thread count form mysqladmin!')
	else:
		debug("DEBUG MYSQL: MYSQL - is %s >= %s?" % (str(t), str(mysql_max_threads)))
		if float(t) >= float(mysql_max_threads):
			debug("DEBUG MYSQL: Yes! returning 1.")
			return 1
		else:
			debug("DEBUG MYSQL: NO! returning 0.")
			return 0

def currdata():
	tests = 'F'
	tmp = {}
	if cpu_stalk == 'T':
		tests = 'T'
		tmp['cpu'] = getcpu()
	if mem_stalk == 'T':
		tests = 'T'
		tmp['mem'] = getmem()
	if mysql_stalk == 'T':
		tests = 'T'
		tmp['mysql'] = getmysql()

	if tests == 'F':
		mailalert('ERROR: no  tests are enabled!')
	return tmp

data = currdata()

# Start out assuming there are no issues
trigger_collect = 'F'

for t in range(0,len(prev)):
	if data.has_key(prev[t]['test']):
		# get the value for the matching item 
		ntest = prev[t]['test']
		nres = data[prev[t]['test']]
		# then remove it from the dictionary, this gives us the elements that aren't in the DB, so we can add them later
		del data[ntest]
		string = "DEBUG: found a match for %s" % (ntest)
		debug(string)
		if int(nres) == 0:
			string = "DEBUG: new result for %s is zero, no problem detected" % (ntest)
			debug(string)
			# if the previous result isn't zero, we need to set it to zero, easier just to make this the default behaviour
			sql = "UPDATE stalk set result=0 where test='%s'" % (ntest)
			cur.execute(sql)
		else:
			# there was a problem and max_alarms is met...
			string = "DEBUG: testing max alarm: %s against count: %s" % (str(max_alarms), str(prev[t]['result']))
			debug(string)
			if int(prev[t]['result']) >= int(max_alarms):
				string = "DEBUG: max alarms reached for: %s, will trigger a collecter run" % (ntest)
				debug(string)
				trigger_collect = 'T'
				# once we execute, should we just set the counter back to 0 and wait for max_alarms again? probably..
				sql = "UPDATE stalk set result=0 where test='%s'" % (ntest)
				cur.execute(sql)
			else:
				# max_alarms wasn't met, so we just increment the counter
				string = "DEBUG: adding increment of one to: %s" % (ntest)
				debug(string)
				sql = "UPDATE stalk set result=%s where test='%s'" % (int(nres) + prev[t]['result'], ntest)
				cur.execute(sql)
 
# we removed found items earlier, if the data dictionary isn't empty at this point, we add the new metrics.
if len(data) > 0:
	for d in data.keys():
		string = "DEBUG: no previous DB entry for %s found, adding one" % (d)
		debug(string)
		sql = "INSERT INTO stalk VALUES ('%s',%s)" % (d, int(data[d]))
		cur.execute(sql)
		debug(sql)
				
# Lastly, we should commit our changes and close our DB handle
if showdebug != 'T':
	conn.commit()
	conn.close()

string = "DEBUG COLLECT: %s" % (trigger_collect)
debug(string)

if trigger_collect == 'T':
	debug('DEBUG COLLECT: fire photon torpedoes!')
	# fire off the script!
	try:
		spcom(collector_timeout, collector)
	except:
		debug("DEBUG COLLECT: FAIL!")
		mailalert("ERROR COLLECTOR: failed trying to execute collector script! Please run your script manually to see what's wrong.", "F")


debug('DEBUG: DB data:')	
if showdebug == 'T':
	print return_query("select * from stalk")
	conn.commit()
	conn.close()
