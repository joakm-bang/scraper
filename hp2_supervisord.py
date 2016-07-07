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
			ip = load(urlopen('https://api.ipify.org?format=json'))['ip']
			goon = False
		except:
			try:
				ip = load(urlopen('http://jsonip.com'))['ip']
				goon = False
			except:
				print('Error getting IP on attempt ' + str(n) + '. Sleeping for ' + str(S) + ' seconds.')
				with open('~/work/IPerrors.log', 'ab') as errorFile:
					errorFile.write('\n' + ctime() + '(' + str(n) + '): IP is ' + str(ip) + '.\n')
				sleep(S)
	return(ip)

with open('/home/joakim/work/startup2.log', 'ab') as logFile:
	tmpStr = ctime() + ': Starting hp2.py'
	statStr = '*'*len(tmpStr) + '\n' + tmpStr + '\n' + '*'*len(tmpStr) + '\n\n' 
	logFile.write(statStr)

with open('/home/joakim/work/startup2.log', 'ab') as logFile:
	tmpStr = ctime() + ': Starting nap'
	logFile.write(tmpStr)
sleep(120)
with open('/home/joakim/work/startup2.log', 'ab') as logFile:
	tmpStr = ctime() + ': Waking up from nap'
	logFile.write(tmpStr)


done = False
t = 0
while not done:
	t = t + 1
	if t == 30:
		#15 minutes already. Try bouncing it.
		print('Rebooting')
		system('sudo reboot')
	ip = getIP()
	if ip != '60.241.126.187':
		done = True
		mess = '\n' + ctime() + ': System ready. Proceeding to start supervisor.\n'
		print(mess)
		with open('/home/joakim/work/startup2.log', 'ab') as logFile:
			logFile.write(mess)
	else:
		mess = ctime() + '(' + str(t) + '): System not ready. Proxy down. Sleeping for 30 seconds.\n'
		print(mess)
		with open('/home/joakim/work/startup2.log', 'ab') as logFile:
			logFile.write(mess)
		sleep(30)


#Start scraping
print('Running "sudo supervisord -n -c ~/work/scraper/supervisord.conf"')
#system('sudo bash ~/work/scraper/startscrapingHP.sh > ~/work/log.log')
system('sudo supervisord -n -c /home/joakim/work/scraper/supervisord.conf')
