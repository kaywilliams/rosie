#!/bin/sh
#
# evaluate openstack server configuration parameters and return
# deploy macros

usage() {

cat &lt;&lt; EOF

Usage: params --name &lt;name> --type &lt;type> 
                               --desc &lt;description> --url &lt;url>
                               --pass &lt;password>

Options:
  --help | -h
      Print usage information
  --name
      Service name, e.g.  "nova"
  --type
      Type of service, e.g. "compute"
  --desc
      Description of the service, e.g. "Nova Compute Service"
  --url
      Url for service, e.g. "http://127.0.0.1:8774/v2/%\(tenant_id\)s"
  --pass
      Password for the service user
EOF

  exit $1
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage 0 ;;
    --name) shift; NAME=$1 ;;
    --type) shift; TYPE=$1 ;;
    --desc) shift; DESC=$1 ;;
    --url) shift; URL=$1 ;;
    --pass) shift; PASS=$1 ;;
    *) shift ;; # ignore
  esac
  shift
done

export OS_USERNAME=admin
export OS_TENANT_NAME=admin
export OS_PASSWORD=%{keystone-admin-password}
export OS_AUTH_URL=http://%{keystone-host}:35357/v2.0/

