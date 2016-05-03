from __future__ import division
import psycopg2
from datetime import datetime, timedelta
import re
from time import sleep, time, ctime

from BeautifulSoup import BeautifulSoup, SoupStrainer
import mechanize
import cookielib
from numpy.random import poisson
from random import sample

from os import path, environ
from dateutil.relativedelta import relativedelta

from json import load
from urllib2 import urlopen


ver = '1.0'

		
class SQLerror(Exception):
	def __init__(self, value='SQL error'):
		print(value)
		with open(settings.errorlog, 'ab') as errorOut:
			errorOut.write(unicode(ctime()) + u' \t' + value + '\n')

class proxyerror(Exception):
	def __init__(self, value='Proxy error'):
		print(value)
		with open(settings.errorlog, 'ab') as errorOut:
			errorOut.write(unicode(ctime()) + u' \t' + value + '\n')

class DBerror(Exception):
	def __init__(self, value='EB error'):
		print(value)
		with open(settings.errorlog, 'ab') as errorOut:
			errorOut.write(unicode(ctime()) + u' \t' + value + '\n')

########################################################################


class Settings:
	""""""
	
	class settingsError(Exception):
		def __init__(self, value='Something went wrong while setting the settings. Probably a bad dropbox path.'):
			print(value)
			with open(settings.errorlog, 'ab') as errorOut:

				errorOut.write(unicode(ctime()) + u' \t' + value + '\n')	
	
	#----------------------------------------------------------------------
	def __init__(self):
		#Defaults
		self.debug = False
		self.bannedIP = None
		self.runlocal = False
		self.runLAN = False
		self.delayLambda = 6
		self.scrapeUsers = False
		self.scrapeMonths = False
		self.scrapeLogs = False
		self.onlyEven = None
		self.chkFreq = 60*5
		self.iterations = 0
		# machine specific variables
		self.dropboxPath = environ['DROPBOX_PATH']
		self.computer = environ['COMPUTER_NAME']
		if self.computer == 'kontoret':  # Kontoret (months, even)
			self.scrapeMonths = True
			self.onlyEven = True
			self.delayLambda = 12
		elif self.computer == 'server':   #Server (users, even)
			self.scrapeUsers = True
			self.onlyEven = True
			self.delayLambda = 12
		elif self.computer == 'hemma':   # Hemma (months, uneven)
			self.runlocal = True
			self.scrapeMonths = True
			self.onlyEven = False
		elif self.computer == 'toshiban':   # Toshiban (logs, uneven)
			self.scrapeLogs = True
			self.onlyEven = False
		elif self.computer == 'litenvit':   # Liten vit (users, uneven)
			self.runLAN = True
			self.scrapeUsers = True
			self.onlyEven = False
			self.bannedIP = '60.241.126.187'
		elif self.computer == 'garderoben':   # Garderoben (logs, even)
			self.runLAN = True
			self.scrapeLogs = True
			self.onlyEven = True
			self.bannedIP = '60.241.126.187'
		else:
			raise settingsError()
		
		self.errorlog = self.dropboxPath + 'Data Incubator/Project/jefit/allusers/errorlogs/' + self.computer + datetime.ctime(datetime.now()).replace(' ', '_').replace(':','_') + '.txt'
		
		#database connection
		self.setDatabase()
	
	def setDatabase(self):
		self.dbconfig = dict()
		self.dbconfig[u'database'] = u'jefit'
		self.dbconfig[u'user'] = environ['PG_USER']
		self.dbconfig[u'password'] = environ['PG_PASS']
		self.dbconfig[u'port'] = 5432
		if self.runlocal:
			self.dbconfig[u'host'] = 'localhost'
		elif self.runLAN:
			self.dbconfig[u'host'] = u'192.168.0.2'
		else:
			self.dbconfig[u'host'] = u'60.241.126.187'
		
		self.herokuconfig = dict()
		self.herokuconfig[u'host'] = 'ec2-54-243-196-76.compute-1.amazonaws.com'
		self.herokuconfig[u'database'] = u'd6rjh7cctk2006'
		self.herokuconfig[u'user'] = environ['HEROKU_USER']
		self.herokuconfig[u'password'] = environ['HEROKU_PASS']
		self.herokuconfig[u'port'] = 5432


# get local settings
settings = Settings()

class database:
	""""""
	
	#----------------------------------------------------------------------
	def __init__(self, dbconfig, connect=True):
		self.dbconfig = dbconfig
		self.connected = False
		self.alivechk = datetime.now() - timedelta(minutes=30)
		self.debug = settings.debug
		if connect:
			self.connect()
    
	#connect to database
	def connect(self):
		config = dict()	
		self.con = psycopg2.connect("dbname={0} user={1} password={2} host={3} port={4}".format(self.dbconfig[u'database'], self.dbconfig[u'user'], self.dbconfig[u'password'], self.dbconfig[u'host'], self.dbconfig[u'port']))
		self.cur = self.con.cursor()
		self.connected = True

	#disconnect
	def close(self):
		if self.con.closed == 0:
			self.con.close()
		self.connected = False
	
	#make column name safe for database
	def safeName(self, x):
		y = unicode(x).lower()
		y = y.replace(u'\xc5', 'a')
		y = y.replace(u'\xc4', 'a')
		y = y.replace(u'\xd6', 'o')
		y = y.replace(u'\xe5', 'a')
		y = y.replace(u'\xe4', 'a')
		y = y.replace(u'\xf6', 'o')
		y = y.replace(u'\xb5', 'u')
		for cr in y:
			crN = ord(cr)
			if (crN < 97 or crN > 122) and (crN < 48 or crN > 57) and crN != 95:
				y = y.replace(cr, u'_')
		return y

	#make string value safe for database (by escaping apostrophes)
	def safeVal(self, x):
		if not (isinstance(x, str) or isinstance(x, unicode)):
			return x
		else:
			return x.replace("'", "''")
	
	
	#insert table
	def insertTable(self, table, cols_types_defaults, pkey=0, debug=settings.debug, showError=True):
		
		class Dummy:			
			def execute(self):				
				colStr = u''
				for n, var in enumerate(self.cols_types_defaults):
					var = list(var)
					colStr = colStr + var[0] + ' ' + var[1] + ' PRIMARY KEY'*(n==self.pkey)
					if len(var) == 3:
						colStr = colStr + ' DEFAULT ' + str(var[2])
					colStr = colStr + ', '
				colStr = colStr.strip(', ')
				
				sql = 'CREATE TABLE {0} ({1})'.format(self.table, colStr)
				self.cur.execute(sql)
				self.con.commit()
				return True
		
		dummy = Dummy()
		dummy.table = table
		dummy.cols_types_defaults = cols_types_defaults
		dummy.pkey = pkey		
		dummy.con = self.con
		dummy.cur = self.cur
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()

	#insert column
	def insertColumn(self, table, col, varType = 'TEXT', default = u'', debug=settings.debug):
		class Dummy:			
			def execute(self):
				if self.col != self.safeName(self.col):
					raise DBerror('Tried to insert unsafe column name')
				if self.default != u'':
					self.default = u' DEFAULT ' + self.default
				self.cur.execute('ALTER TABLE {0} ADD COLUMN {1} {2} {3}'.format(self.table, self.col, self.varType, self.default))
				self.con.commit()
				return True
		dummy = Dummy()
		dummy.table = table
		dummy.col = col
		dummy.varType = varType	
		dummy.default = default
		dummy.safeName = self.safeName		
		dummy.con = self.con
		dummy.cur = self.cur
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()	

	#get existing column names
	def getColumns(self, thisTable, thisScema = None, debug = settings.debug):
		
		class Dummy:
			def execute(self):
				self.cur.execute("select column_name from information_schema.columns where table_name = '{0}';".format(self.thisTable))
				dmp = self.cur.fetchall()
				y = []
				for d in dmp:
					y.append(d[0])
				return y
		
		dummy = Dummy()
		dummy.thisTable = thisTable
		dummy.thisScema = thisScema
		dummy.con = self.con
		dummy.cur = self.cur		
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()		



	#update field in database
	def updateField(self, thisTable, changeVar, newVal, selVar, targetVal, debug=settings.debug):
		class Dummy:
			def execute(self):
				newVal = unicode(self.newVal)
				if isinstance(newVal, bool):
					newVal = unicode(newVal)
				if isinstance(self.targetVal, int) or isinstance(self.targetVal, float):
					self.cur.execute("UPDATE {0} SET {1} = '{2}' WHERE {3} = {4}".format(self.thisTable, self.changeVar, newVal, self.selVar, unicode(self.targetVal)))
					self.con.commit()
				else:
					self.cur.execute("UPDATE {0} SET {1} = '{2}' WHERE {3} = '{4}'".format(self.thisTable, self.changeVar, self.safeVal(newVal), self.selVar, self.targetVal))
					#"UPDATE {0} SET {1} = '{2}' WHERE {3} = '{4}'".format(dummy.thisTable, dummy.changeVar, dummy.safeVal(newVal), dummy.selVar, dummy.targetVal)
					self.con.commit()
				return True
		dummy = Dummy()
		dummy.thisTable = thisTable
		dummy.changeVar = changeVar
		dummy.newVal = newVal
		dummy.selVar = selVar
		dummy.targetVal = targetVal
		dummy.safeVal = self.safeVal
		dummy.con = self.con
		dummy.cur = self.cur		
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()
		
	
	#write to database
	def write2db(self, thisDic, thisTable, useTimeStamp = True, insertKeys=False, debug=settings.debug):	
		class Dummy:
			def execute(self):		
				def makeUnicode(val):
					if type(val) != unicode:
						try:
							val = val.decode('utf-8')
						except:
							try:
								val = unicode(val)
							except:
								pass
					return(val)
				
				Keys = self.thisDic.keys()
				for k in Keys:
					if k != self.safeName(k):
						raise SQLerror('Tried to insert unsafe column name ' + k)
					if self.insertKeys:
						self.insertColumn(self.thisTable, k, 'TEXT')
				
				cols = self.getColumns(self.thisTable)
			
				if self.useTimeStamp:
					if u'db_timestamp' not in cols:
						self.insertColumn(self.thisTable, u'db_timestamp', varType = 'TIMESTAMP')
					self.thisDic[u'db_timestamp'] = 'now'
					Keys = thisDic.keys()
				
				Ss = u''
				keyStr = u''
				inserts = []	
				for key in Keys:
					if self.thisDic[key] != u'null' and self.thisDic[key] is not None:
						inserts.append(self.safeVal(self.thisDic[key]))
						Ss = Ss + u',%s'
						keyStr = keyStr + u',' + key
				#self.cur.execute(u'INSERT INTO ' + self.thisTable + u' (' + keyStr.strip(u',') + u') VALUES (' + Ss.strip(u',') + u')', tuple(inserts))
				self.cur.execute(u'INSERT INTO {0} ({1}) VALUES ({2})'.format(self.thisTable, keyStr.strip(u','), Ss.strip(u',')), tuple(inserts))
				self.con.commit()
				return True
		
		dummy = Dummy()
		dummy.thisTable = thisTable
		dummy.thisDic = thisDic
		dummy.useTimeStamp = useTimeStamp
		dummy.insertKeys = insertKeys
		dummy.safeName = self.safeName
		dummy.insertColumn = self.insertColumn
		dummy.con = self.con
		dummy.cur = self.cur		
		dummy.getColumns = self.getColumns
		dummy.safeVal = self.safeVal
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()
	
	
			

	
	def listCols(self, thisTable, debug=settings.debug):
		class Dummy:
			def execute(self):		
				self.cur.execute("SELECT * FROM " + self.thisTable + " LIMIT 1")
				res = [desc[0] for desc in self.cur.description]
				return(res)
		dummy = Dummy()
		dummy.thisTable = thisTable
		dummy.cur = self.cur		
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()	

	
	def listTables(self, schema = 'public', debug=settings.debug):
		class Dummy:
			def execute(self):		
				self.cur.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema = '{0}'".format(self.schema))
				dmp = self.cur.fetchall()
				res = []
				for d in dmp:
					res.append(d[0])
				return(res)
		dummy = Dummy()
		dummy.schema = schema
		dummy.cur = self.cur		
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()		
	
	
	#drop table
	def dropTable(self, table, debug=settings.debug):
		class Dummy:
			def execute(self):		
				self.cur.execute(u'DROP TABLE {0}'.format(self.table))
				self.con.commit()
				return True
		dummy = Dummy()
		dummy.table = table
		dummy.con = self.con
		dummy.cur = self.cur			
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()
	

	
	# insert list of tuples in table
	def insertMany(self, table, cols, values, debug=settings.debug):
		class Dummy:
			def execute(self):		
				if len(self.values) == 0:
					return False
				ss = ','.join(['%s'] * len(self.values))
				cs = ','.join(self.cols)
				insert_query = 'insert into {0} ({1}) values {2}'.format(self.table, cs, ss)		
				self.cur.execute(insert_query, values)
				self.con.commit()
				return True
		dummy = Dummy()
		dummy.table = table
		dummy.cols = cols
		dummy.values = values
		dummy.con = self.con
		dummy.cur = self.cur
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()	


	
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
					selStr = selStr + "{0} {1} {2} {3} {4} {5}".format(sel[0], sel[1], "'"*isString, str(sel[2]), "'"*isString, ' AND '*(i<len(self.sels)-1))
				
				self.thisCol = listMe(self.thisCol)	
				ncols = len(self.thisCol)
				if ncols > 1:
					self.thisCol = ', '.join(self.thisCol)
				else:
					self.thisCol = self.thisCol[0]
					
				sql = 'SELECT {0} {1} FROM {2} {3} {4}'.format('DISTINCT'*unique, self.thisCol, self.thisTable, selStr, (' limit ' + str(limit))*(limit is not None))
				
				self.cur.execute(sql)
	
				x = self.cur.fetchall()
				
				if ncols == 1:
					y = []
					for xi in x:
						y.append(xi[0])
					return(y)
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
	
	def getSubset(self, thisCol, thisTable, sels=[], unique=False, limit=None, ul=None, ll=None, onlyEven=None, limvar=None, debug=settings.debug):
		if limvar is None:
			if isinstance(thisCol, list) or isinstance(thisCol, tuple):
				limvar = thisCol[0]
			else:
				limvar = thisCol
		if ul is not None:
			sels.append((limvar, '<=', ul))
		if ll is not None:
			sels.append((limvar, '>=', ll))
		if onlyEven is not None:
			sels.append(('mod({0},2)'.format(limvar), '=', 1-onlyEven))
		return self.getValues(thisCol, thisTable, unique=unique, sels=sels, debug=debug, limit=limit)
			
	
	
	def updateMany(self, thisTable, changeVars, newVals, selVar, targetVal, debug=settings.debug):
		class Dummy:
			def execute(self):
				def listMe(x):
					if not (isinstance(x, list) or isinstance(x, tuple)):
						x = [x]
					return x
				self.changeVars = listMe(self.changeVars)
				self.newVals = listMe(self.newVals)
				changes = ''
				for var, val in zip(self.changeVars, self.newVals):
					q = '' + "'"*(isinstance(val, str) or isinstance(val, unicode))
					changes = "{0}{1} = {2}{3}{4}, ".format(changes, var, q, str(val), q)
				changes = changes.strip(', ')
				q = '' + "'"*(isinstance(self.targetVal, str) or isinstance(self.targetVal, unicode))
				self.cur.execute("UPDATE {0} SET {1} WHERE {2} = {3}{4}{5}".format(self.thisTable, changes, self.selVar, q, str(self.targetVal), q))
				self.con.commit()
				return True
		dummy = Dummy()
		dummy.thisTable = thisTable
		dummy.changeVars = changeVars
		dummy.newVals = newVals
		dummy.selVar = selVar
		dummy.targetVal = targetVal
		dummy.safeVal = self.safeVal
		dummy.con = self.con
		dummy.cur = self.cur		
		if not debug:
			return self.timeoutHandler(dummy)
		else:
			return dummy.execute()
		
		
	#tell the database that you're alive
	def imStillAlive(self, debug=settings.debug):
		class Dummy:
			def execute(self):
				computers = heroku.getValues('computer_name', 'monitor_computer')
				if settings.computer not in computers:
					self.write2db({'computer_name':settings.computer, 'ip':br.ip, 'activity':'now', 'email_sent':True, 'speed':0}, 'monitor_computer', useTimeStamp=False)
				else:
					#self.updateField('monitor_computer', 'activity', 'now', 'computer_name', settings.computer)
					#old_ip = br.ip
					br.getIP()
					self.updateMany('monitor_computer', ['activity', 'ip', 'speed'], ['now', br.ip, self.speed], 'computer_name', settings.computer)
					#if old_ip != br.ip:
						#self.updateField('monitor_computer', 'ip', br.ip, 'computer_name', settings.computer)
				return True
		settings.iterations = settings.iterations + 1
		if (datetime.now() - self.alivechk).total_seconds() > settings.chkFreq:
			dummy = Dummy()
			dummy.speed = 60*settings.iterations/(datetime.now() - self.alivechk).total_seconds()
			self.alivechk = datetime.now()
			dummy.updateField = self.updateField
			dummy.updateMany = self.updateMany
			dummy.write2db = self.write2db
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

	def setNoteCounter(self):
		dmp = self.getValues('noteid', tables.notes)
		n = max(dmp)
		n = n + 1
		if settings.onlyEven and (n&1 == 1):
			n = n + 1
		if settings.onlyEven == False and (n&1 == 0):
			n = n + 1
		settings.note_inc = n
		
#This huy queues up users
class userqueue:
	""""""

	#----------------------------------------------------------------------
	def __init__(self, k=1000, maxids=3946679):
		# get users already in list
		self.done = set(db.getValues('userid', tables.users))
		self.queue = []
		self.k = k
		self.maxids = maxids
	
	def __call__(self):
		return self.queue

	def len(self):
		return len(self.queue)
	
	def pop(self, n=-1):
		return self.queue.pop(n)
	
	def isempty(self):
		if self.len() == 0:
			return True
		else:
			return False
	
	def keepEven(self, x, reverse = None):
		if reverse is None:
			return x
		else:
			y = []
			for xi in x:
				if (xi & 1) and (reverse is True):  #odd and looking for odd
					y.append(xi)
				elif not (xi & 1) and not reverse:  #even and looking for even
					y.append(xi)
			return y	

	def addFriends(self, friends, even=None):
		dmp = []
		for friend in friends:
			if friend[1] not in self.done and friend[1] not in self.queue and isinstance(friend[1], int):
				dmp.append(friend[1])
		self.queue = self.queue + self.keepEven(dmp,reverse=even)  # potenitally keep only even or odd user ids
	
	def addtoDone(self, didit):
		self.done.add(didit)

	def fillRandom(self,maxids=False, k=False, even=None):
		if maxids is False:
			maxids = self.maxids
		if k is False:
			k = self.k
		dmp = self.keepEven(list(set(range(1,maxids)).difference(self.done)),reverse=even)
		self.queue = sample(dmp,min(k,len(dmp)))
		
	def fillFriends(self, even=None):
		#dmp = list(set(db.getColVal('user2', tables.friends)).difference(self.done))
		#dmp = self.keepEven(list(set(db.getColVal('user2', tables.friends)).difference(self.done)), even)
		dmp = list(set(db.getValues('user2', tables.friends)).difference(self.done))
		dmp = self.keepEven(list(set(db.getValues('user2', tables.friends)).difference(self.done)), even)
		self.queue = self.queue + dmp
			
		if self.isempty():
			self.fillRandom(self.maxids, self.k, even=even)
			
class monthQueue:
	#----------------------------------------------------------------------
	def __init__(self, only_new_users=True, onlyEven=None, ul=None, ll=None, limit=50000):
		# get unscraped users already in list
		#self.queue = db.getValues(('userid', 'firstdate'), tables.users, sels=[('scraped', '=', False), ('public', '=', True)])
		#self.doneUsers = db.getValues('userid_id', tables.userinfo)
		#self.only_new_users = only_new_users
		#self.queue = db.getSubset(('userid', 'firstdate'), tables.users, sels=[('scraped', '=', False), ('public', '=', True)], onlyEven=self.onlyEven, limit=limit)
		self.onlyEven = onlyEven
		self.limit = limit
		self.ul = ul
		self.ll = ll
		self.refill()
		
	def refill(self):
		self.queue = db.getSubset(('userid', 'firstdate'), tables.users, sels=[('scraped', '=', False), ('public', '=', True)])
	
	def __call__(self):
		return self.queue

	def len(self):
		return len(self.queue)
	
	def pop(self, n=-1):
		pop = self.queue.pop(n)
		#if ((pop[0] not in self.doneUsers) or (self.only_new_users == False)) and ( (self.onlyEven is None) or ((pop[0]&1 == 0 and self.onlyEven == True) or (pop[0]&1 == 1 and self.onlyEven == False)) ):
			#return(pop)
		#else:
			#while (pop[0] in self.doneUsers) or ((pop[0]&1 == 0) != self.onlyEven):
				#pop = self.queue.pop(n)
		return(pop)
			
	
	def isempty(self):
		if self.len() == 0:
			return True
		else:
			return False	

class logQueue:
	#----------------------------------------------------------------------
	def __init__(self, onlyEven = None, ul=None, ll=None, limit=50000):
		
		self.onlyEven = onlyEven
		self.limit = limit
		self.ul = ul
		self.ll = ll		
		self.refill()		
	
	def __call__(self):
		return self.queue

	def refill(self):
		self.queue = db.getSubset(('logid', 'url', 'userid_id'), tables.logs, sels=[('scraped', '=', False)], onlyEven=self.onlyEven, limit=self.limit)
		#dmp = db.getValues(('logid', 'url', 'userid_id'), tables.logs, sels=[('scraped', '=', False)], limit=25000)
		#if self.onlyEven is not None:
			#self.queue = []
			#for xi in dmp:
				#if (xi[0] & 1 == 0) == self.onlyEven:
					#self.queue.append(xi)
		#else:
			#self.queue = dmp

	def len(self):
		return len(self.queue)
	
	def pop(self, n=-1):
		return(self.queue.pop(n))
			
	
	def isempty(self):
		if self.len() == 0:
			return True
		else:
			return False	



#This guy goes to Jefit
class browser:
	""""""
	
	#----------------------------------------------------------------------
	def __init__(self, username=None,password=None,delayLambda=7, path=''):
		
		self.t = [time(), time(), time()]
		self.path = path
		self.errorlog = settings.errorlog
		self.delayLambda = delayLambda
		self.username = username
		self.password = password
		self.summonBrowser()
		self.getIP()
		if username is None:
			self.username = environ['JEFIT_USER']
		else:
			self.username = username
		if password is None:
			self.password = environ['JEFIT_PASS']
		else:
			self.password = password

	
	#----------------------------------------------------------------------
	def summonBrowser(self,headers = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]):
		class NoHistory(object):
			def add(self, *a, **k): pass
			def clear(self): pass
		self.br = mechanize.Browser(history=NoHistory())
		self.cj = cookielib.LWPCookieJar()
		self.br.set_cookiejar(self.cj)
		self.br.set_handle_equiv(True)
		self.br.set_handle_gzip(True)
		self.br.set_handle_redirect(True)
		self.br.set_handle_referer(True)
		self.br.set_handle_robots(False)
		self.br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
		self.br.addheaders = headers
		
	#----------------------------------------------------------------------
	# Don't hammer the server
	def delay(self, minDelay=0.5, printDelay=True):
		delta = (self.t[1]-self.t[0], self.t[2]-self.t[1], time() - self.t[2])
		self.t[0] = time()
		randomDelay = poisson(self.delayLambda)
		napTime = max(randomDelay - delta[2],minDelay)
		if napTime > 0:
			if printDelay:
				print('Total delay:\t' + str(round(sum(delta),2)) + ' seconds\t(' + str(round(delta[0] + delta[2],2)) + ' nap [' + str(round(delta[2],2)) + ' code + ' + str(round(delta[0],2)) + ' extra] and ' + str(round(delta[1],2)) + ' browser).')
			sleep(napTime)	

	#----------------------------------------------------------------------
	#Take a nap if you cannot access the webpage. Probably a timeout error.
	def nap(self, errStr, err, napTime=120):
		try:
			err = unicode(err)
		except:
			try:
				err = str(err).decode('utf-8')
			except:
				try:
					err = str(err).decode('latin-1')
				except:
					err = str(err).decode('ascii', 'ignore')
		divider = u' *'*30
		print(divider + u'\nError at:' + errStr + u'\nError message:\n' + err + u'\nNapping for ' + unicode(napTime/60) + u' minutes\n' + divider)
		with open(self.errorlog, 'ab') as errorOut:
			errorOut.write(unicode(ctime()) + ', ' + errStr + ', ' + err.encode('latin-1') + ', ' + unicode(napTime))
		thisNap = poisson(napTime)
		sleep(thisNap)
	
	#----------------------------------------------------------------------
	#Hit the webpage
	def tryPage(self, targetURL, doForm=None, maxtries=10, napTime=90, mess='Error while opening page', soup=False, noDelay=False):
		goon = True
		tryCount = 0
		while goon == True and tryCount < maxtries:
			tryCount = tryCount + 1
			try:
				if settings.bannedIP is not None:
					self.getIP()
					if settings.bannedIP == self.ip:
						print('Proxy is down.')
						raise proxyerror()
				if not noDelay:
					self.delay()
					self.t[1] = time()
				self.br.open(targetURL)
				self.t[2] = time()
				if isinstance(doForm, int):
					self.br.select_form(nr = doForm)
				elif isinstance(doForm, str) or isinstance(doForm, unicode):
					self.br.select_form(name = doForm)
				if soup:
					s = BeautifulSoup(self.br.response().read())
				goon = False
			except Exception, err:
				self.nap(mess, err, napTime)
				if str(err) == u'HTTP Error 404: Not Found':
					tryCount = maxtries + 5
		heroku.imStillAlive() #announce activity
		if soup and not goon:
			return s
		else:
			return bool(goon - 1)

	#----------------------------------------------------------------------
	#Get public ip
	def getIP(self, maxN=5, S=30):
		n = 0
		goon = True
		while n < maxN and goon:
			try:
				self.ip = load(urlopen('http://jsonip.com'))['ip']
				goon = False
			except:
				print('Error getting IP on attempt ' + str(n) + '. Sleeping for ' + str(S) + ' seconds.')
				sleep(S)

		
	#----------------------------------------------------------------------
	#Set value of html control
	def setCtrl(self, val, name=None, Type=None, nr=None, label=None):
		if name is not None:
			this_ctrl = self.br.form.find_control(name=name)
		elif Type is not None:
			this_ctrl = self.br.form.find_control(type=Type)
		elif nr is not None:
			this_ctrl = self.br.form.find_control(nr=nr)
		elif label is not None:
			this_ctrl = self.br.form.find_control(label=label)
		this_ctrl.value = val
	
	#----------------------------------------------------------------------
	#Login to Jefit
	def login(self):
		self.tryPage('https://www.jefit.com/login/', doForm='register')
		self.setCtrl(self.username, name='vb_login_username')
		self.setCtrl(self.password, name='vb_login_password')
		self.br.submit()
		

#These are various settings
class MonthPage:
	""""""
	
	#----------------------------------------------------------------------
	def __init__(self, soup, getusername=True, getfriends=True, getlogs=True, user=False, singleFriend=False):		
		self.soup = soup
		self.user = user
		self.scraped = None
		
		#check if public
		self.public = True	
		sorry = self.soup.find('div', {'style':'padding: 10px;'})	
		if sorry is not None:
			if sorry.text.find("Sorry, you don't have permission") == 0:
				self.public = False
		
		#get username
		if getusername:
			dmp = self.soup.find('title')
			self.username = dmp.text[:dmp.text.find("'s Logs")]
			
		#get some friends cause you never know when you'll need them
		if getfriends:
			friend_divs = self.soup.findAll('div', {'class':'friendCell2'})
			self.friends = []
			for friend_div in friend_divs:
				if singleFriend:
					self.friends.append(int(friend_div.a['href'].strip('https://www.jefit.com/')))
				else:
					self.friends.append((user, int(friend_div.a['href'].strip('https://www.jefit.com/'))))
		
		#workout logs this month
		if getlogs:
			days = self.soup.findAll('td', {'class':'calenderDay'})
			self.links = set()
			for day in days:
				if day.text != '-':
					imgs = day.findAll('img')
					if len(imgs) > 0:
						if not (len(imgs) == 1 and imgs[0]['src'] == '/images/progresspictures_vector.png'):
							self.links.add(day.a['href'])
			self.links = list(self.links)		
		
			if self.user:
				self.dbrows = []
				for link in self.links:
					#self.dbrows.append((link, datetime.toordinal(datetime.strptime(link[link.rfind('dd=')+3:], '%Y-%m-%d')), False, self.user, None))
					self.dbrows.append((self.user, link, datetime.toordinal(datetime.strptime(link[link.rfind('dd=')+3:], '%Y-%m-%d'))))
	
	def prepare4db(self, firstdate=None, lastdate=None):
		self.todb = dict()
		self.todb['userid'] = self.user
		self.todb['username'] = self.username
		self.todb['public'] = self.public
		self.todb['scraped'] = self.scraped
		if firstdate is not None:
			self.todb['firstdate'] = firstdate
		if lastdate is not None:			
			self.todb['lastdate'] = lastdate
			
		
class ProfilePage:
	""""""
	
	#----------------------------------------------------------------------
	def __init__(self, soup, user, addFriends=True):		
		
		def getDates(soppa, divclass):
			x = soppa.findAll('div', {'class':divclass})
			dates = []
			for xi in x:
				if divclass == 'workoutsessiondatetext':
					s = xi.text							
				s = s.split()
				s[1] = s[1][:-3]
				dates.append(datetime.strptime(' '.join(s), '%B %d %Y'))
			return(dates)
		
		def handleMissing(x):
			age = None
			sex = None
			country = None
			for v in x.split(','):
				if v.lower() in ['male', 'female']:
					sex = v
				else:
					try:
						dmp = int(v)
						age = v
					except:
						country = v
			return(age,sex,country)
			
		self.soup = soup
		self.user = user
		self.oldfriends = []
		
		# Birthyear/sex/country
		x = soup.find('div', {'style':'float:right; margin-right:10px; color:#666666'})
		x = x.text.replace('&nbsp;', ',')
		if x.count(',') == 1:
			(age,sex,country) = handleMissing(x)
		else:
			[age,dmp] = x.split(',',1)
			[sex,country] = dmp.split(',',1)
		if age is not None:
			self.birthyear = datetime.now().year - int(age)
		else:
			self.birthyear = None
		if sex is not None:
			self.sex = (sex.lower().strip() == 'male')
		else:
			self.sex = None
		self.country = country
		
		#Number of friends
		x = soup.findAll('li')
		for i, xi in enumerate(x):
			if xi.img is not None:
				if xi.img['src'] == 'https://www.jefit.com/images/friend_request_20.png':
					break
		self.nfriends = int(xi.text.strip(' Friend(s)'))
		
		#get feed
		feeda = soup.find('a', {'rel':'flowerdivcontainer'})
		feedsoup = br.tryPage(feeda['href'], soup = True, noDelay=True)
		#latest workout dates
		wodates = getDates(feedsoup, 'workoutsessiondatetext')
		if len(wodates) > 0:
			df = min(wodates)
			dl = max(wodates)
			self.lastWO = dl
			self.firstWO = df			
		else:
			self.lastWO = None
			self.firstWO  = None
			
		#The feed cannot be trusted. Only use it to get a feeling for where to start scraping
		#statdates = getDates(feedsoup, 'updatestatfeed')
		#photodates = getDates(feedsoup, 'photofeed')
		
		if addFriends:
			# get current friends and look for new ones
			#self.oldfriends = set(db.getColVal('user2', tables.friends, 'user1', str(user)))
			self.oldfriends = set(db.getValues('user2', tables.friends, sels=[('user1', '=', str(user))]))
			friends = []
			friend_divs = soup.findAll('div', {'class':'friendCell2'})
			for friend_div in friend_divs:
				friend = int(friend_div.a['href'].strip('https://www.jefit.com/'))
				if friend not in self.oldfriends:
					friends.append((user, friend))
					self.oldfriends.add(friend)
			self.newfriends = friends
	
	def writeUserInfo(self):
		#write user info
		outDict = dict()
		outDict['userid_id'] = self.user
		outDict['birthyear'] = self.birthyear
		outDict['male'] = self.sex
		outDict['location'] = self.country
		outDict['nfriends'] = self.nfriends
		if self.firstWO is not None and self.lastWO is not None:
			outDict['firstworkout'] = datetime.toordinal(self.firstWO)
			outDict['lastworkout'] = datetime.toordinal(self.lastWO)
		db.write2db(outDict, tables.userinfo)

	def writeNewFriends(self):
		#add new friends
		if len(self.newfriends) == 0:
			return(True)
		else:
			db.insertMany(tables.friends, ('user1', 'user2'), self.newfriends)
			return(True)
	
	
	def getLogs(self, scrapeddate, maxMiss = 2):
		
		
		def procMonth(t):
			yy = t.year
			mm = t.month
			msoup = br.tryPage('https://www.jefit.com/members/user-logs/?yy=' + str(yy) + '&mm=' + str(mm) + '&xid=' + str(self.user), soup=True)
			mpage = MonthPage(msoup, getusername=False, getfriends=True, getlogs=True, user=self.user, singleFriend=True)
			return(mpage.dbrows, set(mpage.friends))
			
		#intially scraped month
		sdate = firstOfMonth(datetime.fromordinal(scrapeddate))
		scraped = [sdate]
		oldscrapes = db.getValues('scrapeddate', tables.months, sels=[('userid_id', '=', self.user)])
		friends = set([])
		links = []
		
		if self.firstWO is None:
			t1 = sdate
			t2 = sdate
		else:
			t1 = firstOfMonth(self.firstWO)
			t2 = firstOfMonth(self.lastWO)
		
		#from first to last log
		for m in range(0,relativedelta(t2,t1).months+1):
			t = t1 + relativedelta(t1, months=m)
			if (t not in scraped) and (t not in oldscrapes):
				(dmpRows, dmpFriends) = procMonth(t)
				links = links + dmpRows
				friends = friends.union(dmpFriends)
				scraped.append(t)
				emp = (len(dmpRows) == 0)
				print('Middle scrape (' + str(self.user) + ') ' + str(t.year) + '-' + str(t.month) + ' (empty)'*emp + ' (full)'*(1-emp))
		
		#after last log
		misses = 0
		m = 0
		t = t2
		while (misses < maxMiss) and (t < sdate):
			m = m + 1
			t = t2 + relativedelta(t2, months=m)
			if (t not in scraped) and (t not in oldscrapes):
				(dmpRows, dmpFriends) = procMonth(t)
				links = links + dmpRows
				friends = friends.union(dmpFriends)
				scraped.append(t)
				if (len(dmpRows) == 0):
					misses = misses + 1
					print('Foward scrape (' + str(user) + '). Empty month: ' + str(t.year) + '-' + str(t.month) + '\t\t(' + str(misses) + ' misses)')
				else:
					misses = 0
					print('Foward scrape (' + str(user) + '). Full month: ' + str(t.year) + '-' + str(t.month) + '\t\t(' + str(misses) + ' misses)')
		
		#before first log
		mint = datetime.fromordinal(734503)
		misses = 0
		m = 0
		t = t1
		while (misses < maxMiss + 1) and (t >= mint):
			m = m + 1
			t = t1 + relativedelta(t1, months=-m)
			if (t not in scraped) and (t not in oldscrapes):
				(dmpRows, dmpFriends) = procMonth(t)
				links = links + dmpRows
				friends = friends.union(dmpFriends)
				scraped.append(t)
				if (len(dmpRows) == 0):
					misses = misses + 1
					print('Backward scrape(' + str(user) + '). Empty month: ' + str(t.year) + '-' + str(t.month) + '\t\t(' + str(misses) + ' misses)')
				else:
					misses = 0
					print('Backward scrape(' + str(user) + '). Full month: ' + str(t.year) + '-' + str(t.month) + '\t\t(' + str(misses) + ' misses)')
		
		uscraped = []
		for t in scraped:
			uscraped.append((self.user, datetime.toordinal(t)))
		
		return(friends, links, uscraped)


class LogPage:
	""""""
	
	#----------------------------------------------------------------------
	def __init__(self, soup, logid, user, addFriends=True):		
		self.soup = soup
		self.logid = logid
		self.extractLog()
		self.user = user
		if addFriends:
			self.addNewFriends()
		
	
	def writeIt(self, stats=True, summary=True, exercises=True, sets=True, notes = True, friends=True):

		if stats and self.bodyStats != {}:
			self.bodyStats['logid_id'] = self.logid
			db.write2db(self.bodyStats, tables.bodystats)
		if summary and self.summary != {}:
			self.summary['logid_id'] = self.logid
			db.write2db(self.summary, tables.logsummary)
		if notes and self.notes != {}:
			for k in self.notes.keys():
				settings.note_inc = settings.note_inc + 2
				dmp = dict()
				dmp['logid_id'] = self.logid
				dmp['note'] = self.notes[k]
				dmp['noteid'] = settings.note_inc
				dmp['db_timestamp'] = 'now'
				db.write2db(dmp, tables.notes)
		
		for k in self.workouts.keys():
			if exercises and self.workouts != {}:
				ex = self.workouts[k].copy()
				del ex['sets']
				ex['logid_id'] = logid
				exid = ex['logrowid']
				ex['exid'] = exid
				ex['pdate'] = datetime.strptime(ex['date'], "%Y-%m-%d").toordinal()	
				db.write2db(ex, tables.exercises)
				if sets and self.workouts[k]['sets'] != {}:
					for l in self.workouts[k]['sets']:
						Set = dict()
						Set['exid_id'] = exid
						Set['setnumber'] = l + 1
						for m in self.workouts[k]['sets'][l].keys():
							Set[m] = self.workouts[k]['sets'][l][m]
						db.write2db(Set, tables.sets)						

		if friends and len(self.newfriends) > 0:
			db.insertMany(tables.friends, ('user1', 'user2'), self.newfriends)

	def floatMe(self,x):
		try:
			x = float(x)
			return(x)
		except:
			try:
				x = float(x.strip('.'))
				return(x)
			except:
				return(None)
	
	def getTime(self, x):
		dmp = x.split(':')
		return(int(dmp[0])*60**2 + int(dmp[1])*60 + int(dmp[2]))
	
	def splitOnUnit(self, x):
		if x == '' or x is None:
			return(None)
		else:
			dmp = x.split(' ')
			return((float(dmp[0]), dmp[2]))
		
		
		
	def extractLog(self):
		
		#get body stats
		self.bodyStats = dict()
		bps = ['weight', 'fatpercent', 'height', 'chest', 'waist', 'arms', 'shoulders', 'forearms', 'neck', 'hips', 'thighs', 'calves']
		for bp in bps:
			stat = self.soup.find('a', {'href':'/my-jefit/chart/?type=1&bodypart=' + bp})
			if stat is not None:
				txt = stat.text.lower().replace(bp, '').replace('foreams', '').replace('body fat','').strip().strip(':').replace('&nbsp;', '')
				if txt.split(' ')[0] != '0' and txt.split(' ')[0].strip('%').strip() != '0':
					self.bodyStats[bp] = txt
		for v in ['weight', 'height']:
			if v in self.bodyStats.keys():
				dmp = self.bodyStats[v].split(' ')
				self.bodyStats[v] = self.floatMe(dmp[0])
				self.bodyStats[v + '_unit'] = dmp[1]
		if 'fatpercent' in self.bodyStats.keys():
			self.bodyStats['fatpercent'] = self.floatMe(self.bodyStats['fatpercent'].strip('%'))
		for v in ['chest', 'waist', 'arms', 'shoulders', 'forearms', 'neck', 'hips', 'thighs', 'calves']:
			if v in self.bodyStats.keys():
				dmp = self.bodyStats[v].split(' ')
				self.bodyStats[v] = self.floatMe(dmp[0])
				self.bodyStats['length_unit'] = dmp[1]
		

		
		#get summary
		self.summary = dict()
		dmp = self.soup.find('input', {'name':'date'})
		if dmp is not None:
			self.summary['jefitdate'] = dmp['value']
		ses = self.soup.find('div', {'class':'workout-session'})
		if ses is not None:
			self.summary['jefitid1'] = int(ses['id'].strip('workout-session'))
			cats = ['Session Length', 'Actual Workout', 'Wasted Time', 'Rest Timer', 'Exercises Done', 'Weight Lifted']
			divs = ses.findAll('div', {'style':'width:120px; float:left; margin-left:10px;'})
			for div in divs:
				try:
					cat = div.find('div', {'style':re.compile('float:left; width:120px;?')}).text.lower().replace(' ', '_')
					val = div.find('div', {'style':re.compile('float:left; color:#666666; margin-top:5px; width:120px;?')}).text.lower()
					self.summary[cat] = val
				except AttributeError:
					pass
		dmp = self.soup.find('input',{'name':'sessionid'})
		if dmp is not None:
			self.summary['jefitid2'] = int(dmp['value'])

		#make it pretty
		en = 0
		for k in ['wasted_time', 'rest_timer', 'actual_workout', 'session_length']:
			if k in self.summary.keys():
				self.summary[k] = self.getTime(self.summary[k])
			else:
				en = en + 1
		if en > 0:
			with open(settings.errorlog, 'ab') as errorOut:
				errorOut.write(unicode(ctime()) + u' \t Scraped log that appears to be empty (' + str(en) + ' categories): ' + url + '\n')
		if 'weight_lifted' in self.summary.keys():
			dmp = self.splitOnUnit(self.summary['weight_lifted'])
			self.summary['weight_lifted'] = dmp[0]
			self.summary['weight_lifted_unit'] = dmp[1]
		
		#get workout
		self.workouts = dict()
		wos = self.soup.findAll('div', {'class':'exercise-block'})
		for n, wo in enumerate(wos):
			self.workouts[n] = dict()
			dats = wo.findAll('input', {'type':'hidden'})
			for dat in dats:
				nameHack = dat['name']
				if nameHack.lower() == 'logid':
					nameHack = 'jefitlogid'
				self.workouts[n][nameHack] = dat['value']
			sets = wo.findAll('li')
			self.workouts[n]['sets'] = dict()
			
			#deal with cardio workouts
			if wo.find('input', {'name':'cardio'}) is not None:
				self.workouts[n]['sets'][0] = dict()
				block = wo.find('ul', {'class':'logsetlist'})
				lis = block.findAll('li', {'style':'margin-bottom: 5px;'})
				for li in lis:
					litext = li.text.lower().strip(':').strip()
					if litext != 'duration':
						(cat, unit) = litext.split(':')
						cat = db.safeName(cat.strip())
						unit = db.safeName(unit.strip())
						val = li.input['value']
						if val == '' or val is None:
							val = None
						else:
							try:
								val = float(val)
							except:
								val = None
						self.workouts[n]['sets'][0][cat] = val
						self.workouts[n]['sets'][0][cat + '_unit'] = unit
					else:
						inputlogs = li.findAll('input', {'class':'inputlog'})
						for inputlog in inputlogs:
							self.workouts[n]['sets'][0][inputlog['name']] = int(inputlog['value'])
						self.workouts[n]['sets'][0]['totalexseconds'] = int(self.workouts[n]['sets'][0]['hour']*60**2 + self.workouts[n]['sets'][0]['min']*60 + self.workouts[n]['sets'][0]['sec'])
						
			else:
				maxset = 0
				for m, Set in enumerate(sets):
					self.workouts[n]['sets'][m] = dict()
					weight = Set.find('input', {'class':'inputlog decimal'})
					if weight is not None:
						self.workouts[n]['sets'][m][weight['name']] = self.floatMe(weight['value'])
					reps = Set.find('input', {'class':'inputlog'})
					if reps is not None:			
						self.workouts[n]['sets'][m][reps['name']] = self.floatMe(reps['value'])
					
					if self.workouts[n]['recordtype'] == '3':
						self.workouts[n]['sets'][m]['hour'] = int(Set.find('input', {'name':'hour'})['value'])
						self.workouts[n]['sets'][m]['min'] = int(Set.find('input', {'name':'min'})['value'])
						self.workouts[n]['sets'][m]['sec'] = int(Set.find('input', {'name':'sec'})['value'])
						self.workouts[n]['sets'][m]['totalexseconds'] = int(self.workouts[n]['sets'][m]['hour']*60**2 + self.workouts[n]['sets'][m]['min']*60 + self.workouts[n]['sets'][m]['sec'])
		
		#handle missing data in custom exercises
		for n in self.workouts:
			for k in self.workouts[n].keys():
				if self.workouts[n][k] == '':
					self.workouts[n][k] = None
		
		#get notes
		self.notes = dict()
		dmps = self.soup.findAll('table',{'id':'hor-minimalist_2'})
		n = 0
		for dmp in dmps:
			tds = dmp.findAll('td')
			for td in tds:
				if td.strong is not None:
					if td.strong.text == 'Exercise :':
						self.notes[n] = td.text[10:].strip('&nbsp;')
						n = n + 1
		
	def addNewFriends(self):
		# get current friends and look for new ones
		self.oldfriends = set(db.getValues('user2', tables.friends, sels = [('user1', '=', str(self.user))]))
		friends = []
		friend_divs = self.soup.findAll('div', {'class':'friendCell2'})
		for friend_div in friend_divs:
			friend = int(friend_div.a['href'].strip('https://www.jefit.com/'))
			if friend not in self.oldfriends:
				friends.append((user, friend))
				self.oldfriends.add(friend)
		self.newfriends = friends	
		



class Tables:
	
	def __init__(self, setuptables=True):		
		self.users = 'scrape_users'
		self.friends = 'scrape_friends'
		self.logs = 'scrape_logs'
		self.bodystats = 'scrape_bodystats'
		self.userinfo = 'scrape_userinfo'
		self.logsummary = 'scrape_logsummary'
		self.months = 'scrape_months'
		self.exercises = 'scrape_exercises'
		self.sets = 'scrape_sets'
		self.notes = 'scrape_notes'
		if setuptables:
			self.setuptables()
	
	def setuptables(self):
		self.tables = db.listTables()
		if self.users not in self.tables:
			db.insertTable(self.users, [('userid', 'INTEGER'), ('username', 'text'), ('public', 'boolean'), ('scraped', 'boolean', False), ('firstdate', 'integer'), ('lastdate', 'integer'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.friends not in self.tables:
			db.insertTable(self.friends, [('rowid', 'SERIAL'), ('user1', 'INTEGER'), ('user2', 'INTEGER'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.logs not in self.tables:
			db.insertTable(self.logs, [('logid', 'SERIAL'), ('userid_id', 'INTEGER'), ('url', 'TEXT'), ('date', 'INTEGER'), ('scraped', 'BOOLEAN', False), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.bodystats not in self.tables:
			db.insertTable(self.bodystats, [('logid_id', 'INTEGER'), ('weight', 'REAL'), ('weight_unit', 'TEXT'), ('length_unit', 'TEXT'), ('fatpercent', 'REAL'), ('bmi', 'REAL'), ('chest', 'REAL'), ('shoulders', 'REAL'), ('hips', 'REAL'), ('waist', 'REAL'), ('forearms', 'REAL'), ('thighs', 'REAL'), ('arms', 'REAL'), ('neck', 'REAL'), ('calves', 'REAL'), ('height', 'REAL'), ('height_unit', 'TEXT'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.userinfo not in self.tables:
			db.insertTable(self.userinfo, [('userid_id', 'INTEGER'), ('birthyear', 'SMALLINT'), ('location', 'TEXT'), ('male', 'BOOLEAN'), ('nfriends', 'INTEGER'), ('firstworkout', 'INTEGER'), ('lastworkout', 'INTEGER'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.logsummary not in self.tables:
			db.insertTable(self.logsummary, [('logid_id', 'INTEGER'), ('session_length', 'INTEGER'), ('rest_timer', 'INTEGER'), ('actual_workout', 'INTEGER'), ('wasted_time', 'INTEGER'), ('exercises_done', 'INTEGER'), ('weight_lifted', 'REAL'), ('weight_lifted_unit', 'TEXT'), ('jefitdate', 'TEXT'), ('jefitid1', 'INTEGER'), ('jefitid2', 'INTEGER'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.months not in self.tables:
			db.insertTable(self.months, [('rowid', 'SERIAL'), ('userid_id', 'INTEGER'), ('scrapeddate', 'INTEGER'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.exercises not in self.tables:
			db.insertTable(self.exercises, [('exid', 'INTEGER'), ('logrowid', 'INTEGER'), ('myrecord', 'FLOAT'), ('logid_id', 'INTEGER'), ('ename', 'TEXT'), ('recordtype', 'INTEGER'), ('exerciseid', 'INTEGER'), ('belongsys', 'INTEGER'), ('bs', 'INTEGER'), ('date', 'TEXT'), ('eid', 'INTEGER'), ('jefitlogid', 'INTEGER'), ('pdate', 'INTEGER'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.sets not in self.tables:
			db.insertTable(self.sets, [('setid', 'SERIAL'), ('exid_id', 'INTEGER'), ('setnumber', 'INTEGER'), ('rep', 'INTEGER'), ('weight', 'REAL'), ('hour', 'INTEGER'), ('min', 'INTEGER'), ('sec', 'INTEGER'), ('totalexseconds', 'INTEGER'), ('distance', 'REAL'), ('speed', 'REAL'), ('lap_rep', 'REAL'), ('calorie', 'REAL'), ('distance_unit', 'TEXT'), ('speed_unit', 'TEXT'), ('lap_rep_unit', 'TEXT'), ('calorie_unit', 'TEXT'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
		if self.notes not in self.tables:
			db.insertTable(self.notes, [('noteid', 'SERIAL'), ('logid_id', 'INTEGER'), ('note', 'TEXT'), ('db_timestamp', 'TIMESTAMP')] , pkey=0, showError=True)
	
		computers = heroku.getValues('computer_name', 'monitor_computer')
		if settings.computer not in computers:
			heroku.write2db({'computer_name':settings.computer, 'ip':br.ip, 'activity':'now', 'email_sent':True}, 'monitor_computer', useTimeStamp=False)
	
#
# **********************************************************************************************************
# * ------------------------------------------ Code starts here ------------------------------------------ *
# **********************************************************************************************************


#connect to databases
db = database(settings.dbconfig)
heroku = database(settings.herokuconfig)

# open browser and login to Jefit
br = browser(path=settings.dropboxPath + 'Data Incubator/Project/Jefit/allusers/', delayLambda=settings.delayLambda)
br.login()

# set up tables
tables = Tables()
db.setNoteCounter()

# ** Get list of members ** 
if settings.scrapeUsers:
	
	d = datetime.now()
	year = str(d.year)
	month = str(d.month)
	date = datetime.toordinal(d)
	
	# loop over uncollected users
	Q = userqueue()
	Q.fillFriends(even=settings.onlyEven)
	t = datetime.now()
	while not Q.isempty():
		
		# get next user
		user = Q.pop()
		
		#hit user page
		soup = br.tryPage('https://www.jefit.com/members/user-logs/?yy=' + year + '&mm=' + month + '&xid=' + str(user),soup=True)
		monthPage = MonthPage(soup, user=user)
		
		#write users to database
		monthPage.scraped = False
		monthPage.prepare4db(date, date)
		db.write2db(monthPage.todb, tables.users, insertKeys=False)  #writing to users (no need for id fix)
		
		#write friends to database
		db.insertMany(tables.friends, ('user1', 'user2'), monthPage.friends)
		
		#write logs for this month
		if monthPage.public:
			db.insertMany(tables.logs, ('userid_id', 'url', 'date'), monthPage.dbrows)
		
		#add any friends to queue
		Q.addFriends(monthPage.friends, even=settings.onlyEven)
		
		#refill queue if necessary
		if Q.isempty():
			Q.fillRandom(even=settings.onlyEven)
		
		#add user to the done set
		Q.done.add(user)
		
		#print progress
		try:
			print(u'Queued up ' + u'non-'*(1-monthPage.public) + u'public user ' + monthPage.username + u' (' + unicode(user) + u').')
		except UnicodeEncodeError:
			pass
		print('Iteration took ' + str(datetime.now()-t) + ' ' + datetime.ctime(datetime.now()))
		t = datetime.now()

def firstOfMonth(x):
	return(x - relativedelta(x, days = x.day-1))

# ** Go through monthly overviews and get links to individual workout logs ** 
if settings.scrapeMonths:
	
	Q = monthQueue(only_new_users=True, onlyEven=settings.onlyEven)

	t = datetime.now()
	while not Q.isempty():
		
		# get next user
		[user, scrapeddate] = Q.pop()
		
		
		
		#hit profile page
		soup = br.tryPage('https://www.jefit.com/' + str(user),soup=True)
		if soup.find('title').text[:15] == 'JEFIT Community':
			db.updateField(tables.users, 'scraped', True, 'userid', user)
			continue
		profile = ProfilePage(soup, user=user, addFriends=True)
		
		#write new friends
		profile.writeNewFriends()
		
		#start scraping monthly overviews
		(friends, links, scraped) = profile.getLogs(scrapeddate)
		
		#write new friends
		fs = []
		for f in friends:
			fs.append((user, f))
		db.insertMany(tables.friends, ('user1', 'user2'), fs)
		
		#write logs
		db.insertMany(tables.logs, ('userid_id', 'url', 'date'), links)	
		
		#write scraped months
		db.insertMany(tables.months, ('userid_id', 'scrapeddate'), scraped)
		
		#write userinfo
		profile.writeUserInfo()
		
		#don't scrape again for now
		db.updateField(tables.users, 'scraped', True, 'userid', user)
		
		if Q.isempty():
			Q.refill()


#Scrape actual workout sessions

# for time the different tasks
def timeIt(s, text):
	x = (datetime.now() - s).total_seconds()
	print(text)
	print('Time:\t' + str(x))
	return datetime.now()
timeMe = True

if settings.scrapeLogs:
	
	#queue up unscraped logs
	Q = logQueue(settings.onlyEven)
	t = datetime.now()
	while not Q.isempty():
		
		#cardio ID: 9060, https://www.jefit.com/members/user-logs/log/?xid=2254954&dd=2015-01-25
		
		
		# get next user
		s = datetime.now()
		[logid, url, user] = Q.pop()
		if timeMe: s = timeIt(s, 'Popped new user')
		
		#scrape log
		soup = br.tryPage('https://www.jefit.com' + url, soup = True)
		if timeMe: s = timeIt(s, 'Hit webpage')
		log = LogPage(soup, logid, user, addFriends=True)
		if timeMe: s = timeIt(s, 'Extracted log')
		
		
		
		#write to database
		log.writeIt()
		if timeMe: s = timeIt(s, 'Wrote to database')		
		
		#update database queue
		db.updateField(tables.logs, 'scraped', True, 'logid', logid)
		if timeMe: s = timeIt(s, 'Set scraped = True')
		
		#print progress
		print(' Scraped log ' + str(logid) + ' at ' + datetime.ctime(datetime.now()))
		print('Iteration took ' + str(datetime.now()-t) + '\n'*timeMe)
		t = datetime.now()


db.close() #close database connection



