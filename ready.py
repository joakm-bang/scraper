from os import system
from json import load
from urllib2 import urlopen
from time import sleep, ctime

def getIP(maxN=10, S=30):
	ip = False
	n = 0
	goon = True
	while n < maxN and goon:
		try:
			n = n + 1
			ip = load(urlopen('http://api.ipify.org?format=json'))['ip']
			goon = False
		except:
			try:
				ip = load(urlopen('http://jsonip.com'))['ip']
				goon = False
			except:
				print('Error getting IP on attempt ' + str(n) + '. Sleeping for ' + str(S) + ' seconds.')
				sleep(S)
	return(ip)

with open('/home/joakim/work/log.log', 'wb') as logFile:
	tmpStr = ctime() + ': Starting ready.py'
	statStr = '*'*len(tmpStr) + '\n' + tmpStr + '\n' + '*'*len(tmpStr) + '\n\n' 
	logFile.write(statStr)
done = False
t = 0
while not done:
	t = t + 1
	if t == 30:
		#15 minutes already. Try bouncing it.
		system('sudo reboot')
	ip = getIP()
	ping = system('ping -c 1 192.168.0.12')
	if ip != '73.170.245.33' and ping == 0:
		done = True
	else:
		with open('/home/joakim/work/log.log', 'ab') as logFile:
			logFile.write(ctime() + '(' + str(t) + '): System not ready. ' + 'Server not available. '*(ping!=0) + 'Proxy down. '*(ip == '60.241.126.187') + 'Sleeping for 30 seconds.\n')
		sleep(30)

with open('/home/joakim/work/log.log', 'ab') as logFile:
	logFile.write('\n' + ctime() + ': System ready. Proceeding.\n')

#system('gnome-terminal -x tailf ~/work/log.log')
