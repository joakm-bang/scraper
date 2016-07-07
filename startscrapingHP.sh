#!/bin/bash
echo "Starting supervisor: $(date)" > /home/joakim/work/t.log
cd ~/work/scraper/
sudo supervisord -n -c supervisord.conf
exit 0
