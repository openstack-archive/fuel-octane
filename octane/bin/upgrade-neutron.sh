#!/bin/bash

set -ex

SRC=${1:-/etc/neutron}
TMPL=${2:-neutron-template} 

function error {
  echo "Error"
  exit 
}

function exit_success {
  echo "Success"
  exit 
} 

function tmpl_var_names {
	egrep -Rho '%[A-Z_]+%' $1 | sed -r ':a;N;$!ba;s/\n/\l|/g;s/^/^(/;s/$/)/' | sed 's/\(.*\)/\L\1/;s/%//g'
} 

function tmpl_var_values {
	sed -r 's/[ ]+?=[ ]+?/=/g' | awk -F= '/=/ {printf("s/%%%s%%/%s/g;\n", toupper($1), $2)}'
} 

trap error EXIT

echo "Check source and template dirs"
test -d $SRC -a -d $TMPL

echo "Generate variable names"
var_names=`tmpl_var_names $TMPL`

echo "Get values from source dir"
var_values=`egrep -hR "$var_names" $SRC | tmpl_var_values`

cp -vr $TMPL /tmp/neutron
find /tmp/neutron -type f | xargs -tI{} sed -ri'' "$var_values" {} 


trap exit_success EXIT
