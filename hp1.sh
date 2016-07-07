#!/bin/bash
echo "Starting hp1_convpn: $(date)" > /home/joakim/work/hp1.log
cd /home/joakim/work/scraper
sudo python hp1_convpn.py
exit 0
