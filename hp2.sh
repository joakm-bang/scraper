#!/bin/bash
echo "Starting hp2_supervisord: $(date)" > /home/joakim/work/hp2.log
cd /home/joakim/work/scraper
sudo python hp2_supervisord.py
exit 0
