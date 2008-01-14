#!/bin/sh

# place in /etc/cron.daily/spintest.cron

tests=( spintest-r5 spintest-c5 spintest-f6 spintest-f7 spintest-f8 )
num_tests=${#tests[@]}

# compute which slave to test on today
i=$(( `date +%-j` % $num_tests )) # mod of the day of the year
slave=${tests[$i]}

# run tests
xm unpause $slave
ssh root@$slave /root/runtest.sh
xm pause $slave
