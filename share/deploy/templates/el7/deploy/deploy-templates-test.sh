#!/bin/sh
set -e

TEMPLATES_DIR="$(dirname $(dirname $0))"
TEST_DIR="%{test-dir}"
BUILD_FIRST_DEFINITIONS="rsnapshot-server.definition"
SKIP_DEFINITIONS="deploy-packages.definition deploy-basic-config.definition deploy-developer-config.definition deploy-standard-config.definition"

function build {
  echo -e "\nBuilding $1"
  deploy "$1" -l1 --debug \
  --macro "centos-mirror:%{centos-mirror}" \
  --macro "rhel-mirror:%{rhel-mirror}" \
  --macro "rhn-systemid:%{rhn-systemid}" \
  --macro "deploy-remote-host-definition:%{deploy-remote-host-definition}" \
  --macro "deploy-remote-client-pub-keydir:%{deploy-remote-client-pub-keydir" \
  --macro "gpgsign-public:%{gpgsign-public}" \
  --macro "gpgsign-secret:%{gpgsign-secret}" \
  $2 
}

# cleanup test directory 
[ -e $TEST_DIR ] || mkdir -p $TEST_DIR
existing=$(find $TEST_DIR -name "*.definition" -exec basename {} \; | sort)
expected=$(find $TEMPLATES_DIR -name "*.definition" -exec basename {} \; | sort)

for f in $existing; do
  if ! echo $expected | grep -q -P "(^| )$f" ; then
    echo "removing $f"
    rm -f $TEST_DIR/$f
  fi
done

# copy templates to test directory
templates=$(find $TEMPLATES_DIR -name "*.definition")
for f in $templates; do
  cp -f $f $TEST_DIR
done

# modify definitions based on release type
for f in $TEST_DIR/*.definition; do
  sed -i -E "s/(&lt;macro id=['\"]name['\"]>[^&lt;]+)/\1-%{release}/g" $f
done

# build build_first definitions
for f in $(echo $BUILD_FIRST_DEFINITIONS | xargs -n1 | sort | xargs) ; do
    build $TEST_DIR/$f '--macro file-size:6'
done

# filter out build_first and skip definitions
templates=$(find $TEST_DIR -name "*.definition" -printf "%f\n")
for f in $BUILD_FIRST_DEFINITIONS $SKIP_DEFINITIONS; do
  templates=$(echo $templates | sed s/$f//)
done

# build remaining definitions
for f in $(echo $templates | xargs -n1 | sort | xargs) ; do
  extra_args="--macro filesize:6"
  build "$TEST_DIR/$f" "$extra_args"
done
