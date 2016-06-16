#!/bin/bash
cd /home/joakim/work/scraper
git pull origin master
supervisord -n -c supervisord.conf
