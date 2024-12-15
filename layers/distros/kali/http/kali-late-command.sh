test -z "${packer_username##*[[:alnum:]]*}" || (echo "I don't like your username ($packer_username)";exit 1)

useradd -m "$packer_username"
echo "$packer_username ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
mkdir -p "/home/$packer_username/.ssh";
chown "$packer_username:$packer_username" "/home/$packer_username/.ssh"

#url decode
packer_ssh_pubkey=$(echo "$packer_ssh_pubkey" | tr '+' ' ');
printf -v packer_ssh_pubkey '%b' "${packer_ssh_pubkey//%/\\x}";

echo "$packer_ssh_pubkey" >> "/home/$packer_username/.ssh/authorized_keys";
systemctl enable ssh;
systemctl start ssh;
