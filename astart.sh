#!/bin/bash
echo "Getting .ovpn files"
cd /etc/openvpn
wget https://www.privateinternetaccess.com/openvpn/openvpn.zip
echo "Installing unzip"
apt-get -y install unzip
echo "Unzipping file"
unzip -o openvpn.zip
echo "Editing .ovpn file"
echo cp "$1" current.ovpn
cp "$1" current.ovpn
sed -i 's/auth-user-pass/auth-user-pass \/home\/joakim\/work\/.secrets/g' current.ovpn
echo "Create .secrets"
echo $2 > /home/joakim/work/.secrets
echo $3 >> /home/joakim/work/.secrets

