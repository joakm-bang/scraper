from os import system
from json import load
from urllib2 import urlopen
from time import sleep

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
				sleep(S)
	return(ip)

done = False
while not done:
	ip = getIP()
	ping = system('ping -c 1 192.168.0.2')
	if ip != '60.241.126.187' and ping == 0:
		done = True
	else:
		sleep(30)
