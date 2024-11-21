#!/bin/bash -eux

debian_frontend=noninteractive
sudo apt -y update;
sudo apt -y upgrade;
sudo apt -y install dkms build-essential linux-headers-$(uname -r);
(mkdir -p /tmp/VBoxGuestAdditions && sudo mount "$HOME/VBoxGuestAdditions.iso" /tmp/VBoxGuestAdditions -o loop) || true;
sudo /tmp/VBoxGuestAdditions/VBoxLinuxAdditions.run || true;
sudo /opt/VBoxGuestAdditions-*/init/vboxadd setup || exit 0;
