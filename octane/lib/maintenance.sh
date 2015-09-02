#!/bin/bash

export SVC_LIST="/root/services_list"
export SVC_LIST_TMP="${SVC_LIST}.tmp"

enable_apis() {
    $PSSH_RUN "sed -i '/use_backend maintenance if TRUE/d' \
        \$(grep -L 'mode *tcp' /etc/haproxy/conf.d/*)"
    $PSSH_RUN "pkill haproxy"
}

start_corosync_services() {
    $PSSH_RUN "pcs resource \
    | awk '/Clone Set:/ {print \$4; getline; print \$1}' \
    | sed 'N;s/\n/ /' | tr -d :[] \
    | grep Stopped | awk '{print \$1}' \
    | xargs -I@ sh -c \"crm resource start @\""
}

start_upstart_services() {
    local command=$(cat <<EOF
crm_services=\$(pcs resource \
    | awk '/Clone Set:/ {print \$4; getline; print \$1}' \
    | sed 'N;s/\n/ /' \
    | tr -d ':[]' | awk '{print substr(\$1,3)}');
for s in \$(<${SVC_LIST});
do
    for cs in \$crm_services; do
        if [ "\$cs" == "\$s" ]; then
            continue 2;
        fi;
    done;
    start \$s;
done;
EOF
)
    $PSSH_RUN "$command"
}
