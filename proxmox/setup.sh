#!/bin/bash

# Download the container types that we want
pveam download local debian-10-standard_10.*_amd64.tar.gz

# Remove the proxmox "no valid subscription" message
sed -Ezi.bak "s/(Ext.Msg.show\(\{\s+title: gettext\('No valid sub)/void\(\{ \/\/\1/g" /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js
systemctl restart pveproxy.service
