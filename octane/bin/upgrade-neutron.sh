#!/bin/bash

set -ex

SRC=${4:-/etc/neutron} 
TMPL=${3:-neutron-template} 
TEMPLATE_FILE=../patches/neutron-template.tar

function log {
	echo $* > /dev/stderr
} 

function exit_error {
  log "Error"
  exit 1
}

function exit_success {
  log "Success"
  exit 0
} 

function tmpl_var_names {
	egrep -Rho '%[A-Z_]+%' $1 | sed -r ':a;N;$!ba;s/\n/\l|/g;s/^/^(/;s/$/)/' | sed 's/\(.*\)/\L\1/;s/%//g'
} 

function tmpl_var_values {
	sed -r 's/[ ]+?=[ ]+?/=/g' | awk -F= '/=/ {printf("s/%%%s%%/%s/g;\n", toupper($1), $2)}'
} 

function prepare() {
	local TMPL_DIR=$1
	local SRC_DIR=$2
	local OUTPUT_DIR="/tmp/neutron-$$"
	log "Check source and template dirs"
	test -d $SRC_DIR -a -d $TMPL_DIR


	log "Generate variable names"
	var_names=`tmpl_var_names $TMPL_DIR`

	log "Get values from source dir" 
	var_values=`egrep -hR "$var_names" $SRC_DIR | tmpl_var_values`

	cp -r $TMPL_DIR $OUTPUT_DIR

	find $OUTPUT_DIR -type f | xargs -tI{} sed -ri'' "$var_values" {} 

	echo $OUTPUT_DIR
} 

function install() {
	local SRC_DIR=$1
	local DST_DIR=$2
	test -d $SRC_DIR -a -d $DST_DIR
	
	test -z "$NEUTRON_BACKUP" && {
		tar cvf /tmp/neutron-before-upgrade$$.tar $DST_DIR
	} 
	rm -rf $DST_DIR 
	cp -vr $SRC_DIR $DST_DIR
} 

function bootstrap() {
	local NODE=$1
	test -f $0 -a -f ${TEMPLATE_FILE} 
	scp $0 ${TEMPLATE_FILE} ${NODE}:
	ssh ${NODE} "test -d neutron-template || neutron-template; tar xvf `basename $TEMPLATE_FILE` -C neutron-template"
} 

trap exit_error EXIT

case "$1" in
	prepare)
		prepare $2 "/etc/neutron"	
	;;

	install)
		install $2 "/etc/neutron"
	;;

	bootstrap) 
		bootstrap $2
	;;

	*)
		echo "Usage: $0 [prepare|install]"
		exit 1
	
esac

trap exit_success EXIT
