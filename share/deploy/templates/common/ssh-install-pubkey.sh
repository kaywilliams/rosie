#!/bin/bash
#
# Install pubkey in authorized_keys file. The authorized keys file and 
# any parent folders will be created if they do not exist.
#
# Accepts two parameters:
# * path to the publish key
# * path to the authorized keys file

set -e

# set convenience variables
pubkey=$1
authkeys=$2
sshdir=$(dirname $authkeys)

# make sshdir if it doesn't exist
[[ -d $sshdir ]] || mkdir $sshdir 

# create authorized_keys file if it doesn't exist
[[ -f $authkeys ]] || touch $authkeys

# copy pubkey into authorized keys if it's not there already
[[ $(cat $authkeys) == *$(cat $pubkey)* ]] || echo $(cat $pubkey) >> $authkeys
  
# set permissions
chmod 700 $sshdir
chmod 600 $authkeys
