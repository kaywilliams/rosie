#! /bin/bash
TMPLDIR=/var/www/html/templates

rm -rf $TMPLDIR
cp -aL ../../share/deploy/templates $TMPLDIR
chown -R apache:apache $TMPLDIR
restorecon -R $TMPLDIR
