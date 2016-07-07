#!/bin/bash
echo "Taking nap: $(date)" > /home/joakim/work/t.log
sleep 180
echo "Starting supervisor: $(date)" >> /home/joakim/work/t.log
cd ~/work/scraper/
sudo supervisord -n -c supervisord.conf
exit 0
