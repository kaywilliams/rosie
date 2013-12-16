#!/bin/bash
#
# Creates ssh rsa public and private keys. Private keys are in two formats
# pub and pem
#
# Accepts two parameters:
# * the folder where the keys should be created
# * the fully qualified domain name of the host that will be using the keys

set -e

# create ssh key
if ! [ -f $1/id_rsa ]; then
  [ -d $1 ] || mkdir $1
  cd $1

  # create key
  ssh-keygen -q -t rsa -b 2048 -f id_rsa -N ""

  #strip user@hostname from public key
  cat id_rsa.pub | cut -d' ' -f 1-2 > id_rsa.pub.new
  mv id_rsa.pub.new id_rsa.pub

  # create pem encoded public key
  openssl req -x509 -days 365 -new -key id_rsa -out id_rsa.pem -batch

  cd - >/dev/null

  # remove existing key from build machine known_hosts
  [ -f /root/.ssh/known_hosts ] && sed -i '/$2/d' /root/.ssh/known_hosts || :
fi
