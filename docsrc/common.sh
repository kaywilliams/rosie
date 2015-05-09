#! /bin/bash

if [[ $1 = "--clean-tmpdir" ]]; then
  tmpdir=./tmp/en-US
  if [ -d $tmpdir ]; then
    rm -rf $tmpdir/$2 $tmpdir/xml $tmpdir/xml_tmp
  fi 
fi
