#!/bin/sh

#set -x
childs=""

state_cache_cleanup() {
	#find . -iname ".*" -type f -delete
	rm -v .network_*
} 

state_name() {
	echo $1 | sed 's/[^a-z0-9]/_/g;s/^/./'
}

state_save() {
	echo $2 > `state_name "$1"`
}

state_get() {
	local file=`state_name "$1"`
	test -f $file && {
 		exit_code=`cat $file`
		return $exit_code
	}
	return 255
}

state_is_change() {
	state_get "$1"
	local old_state=$?
	local current_state=$2
	local current_state_txt="true"
	#echo "compare $current_state and $old_state"

	if [ $current_state -ne 0 ]; then
		current_state_txt="false"
		current_state=1
	fi

	if [ $old_state -eq 255 ]; then
		echo `date "+%s"` $1 null "->" $current_state_txt
		return 1
	fi

	if [ $old_state -ne $current_state ]; then
		echo `date "+%s"` $1 $old_state "->" $current_state_txt
		return 1
	fi
	return 0
}


_do_run() {
	local description="$1"
	shift
	run_cmd=$*
	while :; do
		$run_cmd > /dev/null 2>&1
		new_state=$?
                #echo $run_cmd $new_state
		state_is_change "$description" $new_state
		state_save "$description" $new_state
                sleep 1
	done
}

do_run() {
    name="$1"
    shift
    _do_run "$name" $* &
    childs="$childs $!"
}

state_cache_cleanup


while [ -n "$*" ]; do
	do_run "network avialability ${1}" ping -c3 -W2 $1
	shift
done
is_run=1

trap "is_run=''" 2 15

while [ ! -z "$is_run" ] ; do
    sleep 1;
done

for child in $childs; do
    echo stop child $child
    kill -9 $child
done

