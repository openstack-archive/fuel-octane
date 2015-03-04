#!/bin/sh 
set -ex

export SSH_ARGS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
#echo 'select floating_ip_address from floatingips;' | mysql -s neutron | xargs -P5 -I% sh -c "sshpass -p'cubswin:)' scp cirros_timeline* $SSH_ARGS cirros@% id || :"

floating_ip=`echo "select floating_ip_address from floatingips;" | mysql -s neutron | tr "\n" " "`

cat<<EOF > cirros_timeline_wrapper.sh
#!/bin/sh
sh /home/cirros/cirros_timeline.sh $floating_ip > /home/cirros/output.txt 2>&1 &
EOF

echo -n $floating_ip | xargs -d" " -P5 -I% sh -c "sshpass -p'cubswin:)' scp $SSH_ARGS cirros_timeline* cirros@%: || :"
echo -n $floating_ip | xargs -d" " -P5 -I% sh -c "sshpass -p'cubswin:)' ssh $SSH_ARGS cirros@% sh ./cirros_timeline_wrapper.sh"
