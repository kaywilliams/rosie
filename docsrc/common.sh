#! /bin/bash

if [[ $1 = "--copy-templates" ]]; then
  TMPLDIR=/var/www/html/templates
  rm -rf $TMPLDIR
  cp -aL ../../share/deploy/templates $TMPLDIR
  chown -R apache:apache $TMPLDIR
  restorecon -R $TMPLDIR
fi

if [[ $1 = "--clean-tmpdir" ]]; then
  tmpdir=./tmp/en-US
  if [ -f $tmpdir ]; then
    rm -rf $tmpdir/$2 $tmpdir/xml $tmpdir/xml_tmp
  fi 
fi
