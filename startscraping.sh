#!/bin/bash
echo "Waiting for system to get ready: $(date)" > /home/joakim/work/t3.log
python /home/joakim/work/scraper/ready.py
echo "Staring to scarpe: $(date)" >> /home/joakim/work/t3.log
cd /home/joakim/work/scraper/
sudo supervisord -n -c supervisord.conf
exit 0
