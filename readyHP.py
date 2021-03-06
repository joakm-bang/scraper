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
				sleep(S)
	return(ip)

with open('/home/joakim/work/startup.log', 'wb') as logFile:
	tmpStr = ctime() + ': Starting readyHP.py'
	statStr = '*'*len(tmpStr) + '\n' + tmpStr + '\n' + '*'*len(tmpStr) + '\n\n' 
	logFile.write(statStr)

#Check connection
done = False
t = 0
while not done:
	t = t + 1
	if t == 15:
		#20 minutes already. Try bouncing it.
		system('sudo reboot')
	ping = system('ping -c 1 60.241.126.187')
	if ping == 0:
		done = True
	else:
		with open('/home/joakim/work/startup.log', 'ab') as logFile:
			logFile.write(ctime() + '(' + str(t) + '): No connection. Restarting network service and sleeping for 90 seconds.\n')
		system('sudo service network-manager restart')
		sleep(90)

# Pull from git
#with open('/home/joakim/work/startup.log', 'ab') as logFile:
#	logFile.write('\n' + ctime() + ': Connection established. Proceeding to pull from git.\n')
#gitpull = system('sudo bash ~/work/scraper/gitpull.sh')

# Connect to VPN
with open('/home/joakim/work/startup.log', 'ab') as logFile:
	logFile.write('\n' + ctime() + ': Pulled from git (' + str(gitpull) + '). Proceeding to connect VPN.\n')
system('sudo bash /home/joakim/work/scraper/convpn.sh')
