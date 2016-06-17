#!/bin/bash
echo "Staring to scarpe: $(date)" > /home/joakim/work/t3.log
cd /home/joakim/work/scraper/
sudo supervisord -n -c supervisord.conf
exit 0
