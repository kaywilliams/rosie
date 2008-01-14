#!/bin/sh

# test script for spin test machines

# environment
export PATH=$PATH:~/devtools/bin
export PYTHONPATH=~/spin:~/rendition-common:$PYTHONPATH

# setup
if [ ! -e ~/rendition-common ]; then
  hg clone https://www.renditionsoftware.com/hg/rendition-common
else
  cd ~/rendition-common
  hg pull
  hg update
  cd -
fi

if [ ! -e ~/spin ]; then
  hg clone https://www.renditionsoftware.com/hg/spin
else
  cd ~/spin
  hg pull
  hg update
  cd -
fi

if [ ! -e ~/devtools ]; then
  hg clone https://www.renditionsoftware.com/hg/devtools
else
  cd ~/devtools
  hg pull
  hg update
  cd -
fi

# testing
cd ~/spin/spintest
for basedistro in redhat-5 centos-5 fedora-6 fedora-7 fedora-8; do
  echo Testing base distro $basedistro...
  python runtest.py --base-distro $basedistro \
                    --share-path ~/spin/share/spin \
                    --log-level 1
done
exit # with status code from the above call
