from __future__ import division
import psycopg2
from datetime import datetime, timedelta
from time import sleep, time, ctime

from os import path, environ, system


class Settings:
	""""""
	
	#----------------------------------------------------------------------
	def __init__(self):
		#Defaults
		self.debug = False
		self.dropboxPath = environ['DROPBOX_PATH']
		self.computer = environ['COMPUTER_NAME']
		self.errorlog = self.dropboxPath + 'Data Incubator/Project/jefit/allusers/errorlogs/' + \
		    self.computer + datetime.ctime(datetime.now()).replace(' ', '_').replace(':','_') + '.txt'
		
		
		#database connection
		self.setDatabase()
	
	def setDatabase(self):
		self.herokuconfig = dict()
		self.herokuconfig[u'host'] = 'ec2-54-243-196-76.compute-1.amazonaws.com'
		self.herokuconfig[u'database'] = u'd6rjh7cctk2006'
		self.herokuconfig[u'user'] = environ['HEROKU_USER']
		self.herokuconfig[u'password'] = environ['HEROKU_PASS']
		self.herokuconfig[u'port'] = 5432


settings = Settings()

class database:
	""""""
	
	#----------------------------------------------------------------------
	def __init__(self, dbconfig, connect=True):
		self.dbconfig = dbconfig
		self.connected = False
		if connect:
			self.connect()
    
	#connect to database
	def connect(self):
		config = dict()	
		self.con = psycopg2.connect("dbname={0} user={1} password={2} host={3} port={4}".format(
		    self.dbconfig[u'database'], 
		    self.dbconfig[u'user'], 
		    self.dbconfig[u'password'], 
		    self.dbconfig[u'host'], 
		    self.dbconfig[u'port']))
		self.cur = self.con.cursor()
		self.connected = True
		
	#disconnect
	def close(self):
		if self.con.closed == 0:
			self.con.close()
		self.connected = False
			
	#Read column values
	def getValues(self, thisCol, thisTable, unique = False, sels = [], debug=settings.debug, limit=None):
		class Dummy:
			def execute(self):		
				def listMe(x):
					if isinstance(x, list) or isinstance(x, tuple):
						return(x)
					else:
						return([x])
				
				selStr = 'WHERE '*(len(self.sels) > 0)
				for i, sel in enumerate(listMe(self.sels)):
					isString = (isinstance(sel[2], str) or isinstance(sel[2], unicode))
					selStr = selStr + "{0} {1} {2}{3}{4} {5}".format(
					    sel[0], 
					    sel[1], 
					    "'"*isString, 
					    str(sel[2]), 
					    "'"*isString, 
					    ' AND '*(i<len(self.sels)-1))
				
				self.thisCol = listMe(self.thisCol)	
				ncols = len(self.thisCol)
				
				if ncols > 1:
					self.thisCol = ', '.join(self.thisCol)
				else:
					self.thisCol = self.thisCol[0]
					
				sql = 'SELECT {0} {1} FROM {2} {3} {4}'.format(
				    'DISTINCT'*unique, 
				    self.thisCol, 
				    self.thisTable, 
				    selStr, 
				    (' limit ' + str(limit))*(limit is not None))
				
				self.cur.execute(sql)
	
				x = self.cur.fetchall()
				
				if ncols == 1:
					y = []
					for xi in x:
						y.append(xi[0])
					if len(y) == 1:
						return y[0]
					else:
						return(y)
				else:
					if len(x) == 1:
						return x[0]
					else:
						return(x)
				
		dummy = Dummy()
		dummy.thisCol = thisCol
		dummy.thisTable = thisTable
		dummy.unique = unique
		dummy.sels = sels
		dummy.con = self.con
		dummy.cur = self.cur
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()		

	def timeoutHandler(self, obj):
		n = 0
		while (n < 11):
			n = n + 1
			try:
				if (self.con.closed > 0):
					self.connect()
				obj.con = self.con
				obj.cur = self.cur
				return obj.execute()
			except Exception as e:
				print('Database error:\t{0}').format(str(e))
				with open(settings.errorlog, 'ab') as errorOut:
					errorOut.write(','.join((ctime(),str(e))))
				try: 
					self.con.rollback()
				except:
					pass
				try:
					self.close()
				except:
					pass
				print('Iteration {0}. Sleeping for 1 minute.'.format(str(n)))
				sleep(60)
				try:
					try:
						self.close()
					except:
						pass
					self.connect()
				except:
					pass
		raise DBerror('Fatal databse error.')


heroku = database(settings.herokuconfig)

#start supervisord
#system('supervisord -n -c /etc/supervisord.conf')

while True:
	#get latest activity
	lastact = heroku.getValues('activity', 'monitor_computer', sels=[('computer_name', '=', settings.computer)])
	#check if it's 15 minutes late
	lastact = lastact.replace(tzinfo=None)
	lastact = lastact + timedelta(hours=10)
	tminus15 = datetime.now() - timedelta(minutes=15)
	if lastact < tminus15:
		system('supervisorctl signal HUP all')
		with open(settings.dropboxPath + 'Data Incubator/Jefit/logs/' + settings.computer + '_log.txt', 'ab') as logFile:
			logFile.write('Restart at \t' + ctime() + '\n')
		print(ctime() + ':\t Restarted script.')
	else:
		print(ctime() + ':\t Script is running fine.')
	sleep(60*3)
	
system('sudo unlink /tmp/supervisor.sock')
	
