#!/bin/bash
sleep 2s
echo "Running git: $(date)" > /home/joakim/work/t2.log
cd /home/joakim/work/scraper
sudo git pull origin master
exit 0
