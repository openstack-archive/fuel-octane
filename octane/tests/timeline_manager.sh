#!/bin/sh
set -e

export SSH_ARGS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=QUIET"
#echo 'select floating_ip_address from floatingips;' | mysql -s neutron | xargs -P5 -I% sh -c "sshpass -p'cubswin:)' scp cirros_timeline* $SSH_ARGS cirros@% id || :"

floating_ip=`echo "select floating_ip_address from floatingips where status = 'ACTIVE';" | mysql -s neutron | tr "\n" " "`

WRAPPER_SCRIPT="cirros_timeline_wrapper.sh"
P=10

show_help() {
                cat<<EOF
Usage $0 <action>
Actions:
        start
        stop
        show
        restart
EOF

}

test -f ${WRAPPER_SCRIPT}0 || {
cat <<EOF > $WRAPPER_SCRIPT
#!/bin/sh
case \$1 in
        start)
                sh \$0 status >/dev/null
                if [ \$? -ne 0 ]; then
                        echo Already started
                        exit 1
                fi
                sh /home/cirros/cirros_timeline.sh $floating_ip > /home/cirros/output.txt 2>&1 &
                sh \$0 status
        ;;
        stop)
                kill \`ps auxw|grep -i timeline.sh | grep -v grep | awk '{print \$1}'\` >/dev/null 2>&1
                sleep 3
                sh \$0 status
        ;;
        show)
                cat /home/cirros/output.txt | egrep '^[0-9]'
        ;;
        status)
                out=\`ps auxw|grep -i timeline.sh | grep -v grep\`
                echo -n "status "
                if [ -z "\$out" ]; then
                                echo "stopped"
                        exit 0
                        else
                                echo "started"
                        exit 1
                fi
        ;;
        restart)
                sh \$0 status && sh \$0 stop
                sh \$0 start
        ;;
        *)
                echo "Unknown option $1"
                exit 2
        ;;
esac
EOF
chmod +x $WRAPPER_SCRIPT
}


case $1 in
        start)
        ;;
        stop)
        ;;
        restart)
        ;;
        status)
        ;;
        show)
                P=1
        ;;
        help)
                show_help
                exit 0
        ;;
        *)
                show_help
                exit 1
        ;;
esac

echo -n $floating_ip | xargs -d" " -P${P} -I% sh -c "sshpass -p'cubswin:)' scp $SSH_ARGS cirros_timeline* cirros@%: | sed 's/^/% /'"
echo -n $floating_ip | xargs -d" " -P${P} -I% sh -c "sshpass -p'cubswin:)' ssh $SSH_ARGS cirros@% sh ./cirros_timeline_wrapper.sh $1 | sed 's/^/% /'"


