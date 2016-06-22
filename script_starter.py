from __future__ import division
from time import ctime, sleep
from os import system

sleep(60)
with open('/home/joakim/work/log.log', 'ab') as logFile:
	logFile.write(ctime() + ':\t Starting log.\n')

system('supervisorctl -c /home/joakim/work/scraper/supervisord.conf restart all')
with open('/home/joakim/work/restarts.log', 'ab') as logFile:
	logFile.write(ctime() + ':\t Logged in and restarted supervisor.\n')

	
	
