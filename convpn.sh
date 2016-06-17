#0!/bin/bash
echo "Connecting to VPN: $(date)" > /home/joakim/work/t1.log
cd /etc/openvpn/
sudo openvpn current.ovpn
exit 0
