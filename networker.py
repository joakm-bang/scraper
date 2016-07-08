from os import system
from json import load
from urllib2 import urlopen
from time import ctime


def getIP(maxN=5, S=30):
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
				sleep(S)
	return(ip)

ip = getIP()
if ip != '60.241.126.187':
	system('service network-monitor restart')
	with open('/home/joakim/work/network.log', 'ab') as logFile:
		logFile.write(ctime() + ': Network restarted\n')
else:
	with open('/home/joakim/work/network.log', 'ab') as logFile:
		logFile.write(ctime() + ': Network is fine.\n')
	
