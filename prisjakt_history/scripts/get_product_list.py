from __future__ import division
#from bs4 import BeautifulSoup
from BeautifulSoup import BeautifulSoup
from time import sleep
from datetime import datetime, timedelta
import requests
import re
import os
import dill
import csv
import numpy as np
from random import shuffle
import json
import time

class Delayer:

	def __init__(self, Lambda=4):
		self.last = datetime.now()
		self.Lambda = Lambda

	def delay(self):
		nap = max(1,np.random.poisson(self.Lambda) - (datetime.now() - self.last).seconds)
		print 'Sleeping {0} seconds... '.format(str(nap))
		self.last = datetime.now()
		sleep(nap)


delayer = Delayer()

cname = os.environ['COMPUTER_NAME'] 		# computer name
# paths
#base_path = 'c:/work/prisjakt_history/'
base_path = '/media/joakim/Storage/Dropbox/now/prisjakt_history/'
if cname.startswith('vbox'):
	base_path = '/home/joakim/work/scraper/prisjakt_history/'
prod_list_baseurl = 'https://www.prisjakt.nu/butiksinfo.php?f=659&lista=prod&s='
product_baseurl = 'https://www.prisjakt.nu/produkt.php?pu='
dustin_productlist_path = base_path + 'dustin_product_list/'
dustin_product_path = base_path + 'dustin_products/'
results_path = base_path + 'results/'
price_history_path = base_path + 'price_history/'

def get_page(n):

	fname = dustin_productlist_path + 'dustin_product_page_{0}.dill'.format(str(n))
	if not os.path.exists(fname):
		delayer.delay()
		r = requests.get('{0}{1}'.format(prod_list_baseurl, str(n)))
		with open(fname, 'wb') as out_file:
			dill.dump(r, out_file)
		print '{0} (scraped)'.format(str(n))
	else:
		with open(fname, 'rb') as in_file:
			r = dill.load(in_file)
	return r
	
# Get all Dustin products
product_ids_file = results_path + 'product_ids.dill'
if not os.path.exists(product_ids_file):
	pids = [] 		# list of product ids
	for n in xrange(0,16600,100):
		r = get_page(n)
		soup = BeautifulSoup(r.text, 'lxml')
		script = str(filter(lambda x: str(x).startswith('<script type="text/javascript">\n//Data for expansions'), soup.findAll('script'))[0])
		
		new_pids = json.loads(script[276:script.rfind(']};')+2]).keys()
		if len(new_pids) < 100:
			print n, len(new_pids)
		pids = pids + new_pids	
	# save results
	with open(product_ids_file, 'wb') as out_file:
		dill.dump(pids, out_file)
else:
	# load results
	with open(product_ids_file, 'rb') as out_file:
		pids = dill.load(out_file)


def get_product_page(pid):
	fname = dustin_product_path + 'dustin_product_{0}.dill'.format(str(pid))
	if not os.path.exists(fname):
		delayer.delay()

		goon = True
		n_tries = 0
		while goon and n_tries < 10:
			try:
				r = requests.get('{0}{1}'.format(product_baseurl , str(pid)))
				goon = False
			except:
				print 'Error number {0} in product page'.format(str(n_tries + 1))
				sleep(30)
				n_tries = n_tries + 1
		with open(fname, 'wb') as out_file:
			dill.dump(r, out_file)
		print '{0} (scraped)'.format(str(pid))		
	else:
		with open(fname, 'rb') as in_file:
			r = dill.load(in_file)
	return r


def get_price_history(pris_id, produkt_id):
	fname = price_history_path + 'price_history_{0}_{1}.dill'.format(str(pris_id), str(produkt_id))
	if not os.path.exists(fname):
		delayer.delay()
		t = str(int(float(time.time())*1000)) 			# time stamp
		ID = str(int(int(produkt_id)/79))[:3]				# bullshit ID
		url = 'https://www.prisjakt.nu/ajax/jsonajaxserver.php?m=get_prod_prishist&p={"pris_id":' + str(pris_id) + ',"produkt_id":' + str(produkt_id) + '}&t=' + t + '&id=' + ID

		goon = True
		n_tries = 0
		while goon and n_tries < 10:
			try:
				r = requests.get(url)
				goon = False
			except:
				print 'Error number {0} in price history page'.format(str(n_tries + 1))
				sleep(30)
				n_tries = n_tries + 1

		with open(fname, 'wb') as out_file:
			dill.dump(r, out_file)
	else:
		with open(fname, 'rb') as in_file:
			r = dill.load(in_file)
	return r
	
# scrape product pages
products_file = results_path + 'products.dill'
pat = re.compile(r'^show_price_hist_for_price_id.*$')
pat2 = re.compile(r'^show_price_hist_for_price_id\((\d*), (\d*)\)$')
def parse_ids(link):
	[int(k) for k in re.match(pat2, link['onclick']).groups()]


# divide workload
if cname != 'monstret':
	cut = int(cname.strip('vbox'))*2000
	pids = pids[cut:]

for pid in pids:

	r = get_product_page(pid)
	soup = BeautifulSoup(r.text, 'lxml')
	content = soup.find('div', {'class':"contentblock"})	
	links = content.findAll('a', {'onclick':pat})
	ids_list = list(set(map(lambda x: tuple([int(k) for k in re.match(pat2, x['onclick']).groups()]), links)))
	for ids in ids_list:
		rp = get_price_history(ids[1], ids[0])
	
