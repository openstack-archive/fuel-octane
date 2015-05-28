#!/bin/bash

disable_wsrep() {
    [ -z "$1" ] && die "No node ID provided, exiting, exiting"
    ssh root@$1 "echo \"SET GLOBAL wsrep_on='off';\" | mysql"
}

enable_wsrep() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    ssh root@$1 "echo \"SET GLOBAL wsrep_on='ON';\" | mysql"
}
