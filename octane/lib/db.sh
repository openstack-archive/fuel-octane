#!/bin/bash -xe

disable_wsrep() {
    [ -z "$1" ] && die "No node ID provided, exiting, exiting"
    ssh root@node-$1 "echo \"SET GLOBAL wsrep_on='off';\" | mysql"
}

enable_wsrep() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    ssh root@node-$1 "echo \"SET GLOBAL wsrep_on='ON';\" | mysql"
}

xtrabackup_install() {
    [ -z "$1" ] && die "No node ID provided, exiting"
    ssh root@node-$1 "yum -y install percona-xtrabackup.x86_64"
}

xtrabackup_stream_from_node() {
    [ -z "$1" ] && die "No backup source node ID provided, exiting"
    ssh root@node-$1 "xtrabackup --backup --stream=tar ./ | gzip " \
        | cat - > /tmp/dbs.original.tar.gz
}

xtrabackup_from_env() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    local node=$(list_nodes $1 controller | head -1)
    xtrabackup_install $node
    disable_wsrep $node
    xtrabackup_stream_from_node $node
    enable wsrep $node
}

xtrabackup_restore_to_env() {
    [ -z "$1" ] && die "No env ID provided, exiting"
    local cics=$(list_nodes $1 controller)
    echo $cics | xargs -I{} ssh root@{} \
        "mv /var/lib/mysql/grastate.dat /var/lib/mysql/grastate.old"
    echo $cics | head -1 | xargs -I{} bash -c \
        "cat /tmp/dbs.original.tar.gz \
        | ssh root@{} 'cat - > /var/lib/mysql/dbs.original.tar.gz'"
    echo $cics | head -1 | xargs -I{} ssh root@{} \
        "cd /var/lib/mysql;
        tar -zxvf db.original.tar.gz;
        chown -R mysql:mysql /var/lib/mysql;
        export OCF_RESOURCE_INSTANCE=p_mysql;
        export OCF_ROOT=/usr/lib/ocf;
        export OCF_RESKEY_socket=/var/run/mysqld/mysqld.sock;
        export OCF_RESKEY_additional_parameters="\""--wsrep-new-cluster"\"";
        /usr/lib/ocf/resource.d/mirantis/mysql-wss start;"
    echo $cics | tail -n +2 | xargs -I{} ssh root@{} \
        "export OCF_RESOURCE_INSTANCE=p_mysql;
        export OCF_ROOT=/usr/lib/ocf;
        export OCF_RESKEY_socket=/var/run/mysqld/mysqld.sock;
        /usr/lib/ocf/resource.d/mirantis/mysql-wss start;"
}
