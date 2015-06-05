#!/bin/bash -x

host=${1:-"cz5545-fuel"}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}

version=$(awk -F\" '/version/{print $2}' < setup.py)
wheel="octane_nailgun-${version}-py2-none-any.whl"

git push --force $host HEAD
# TODO: Next lines can be separated in independent script tnat can be
#       copied into $host and runned from there.
ssh $host "cd octane; git reset --hard $branch"
ssh $host "cd octane; git clean -x -d -f"
ssh $host "cd octane/octane_nailgun; python setup.py bdist_wheel"
# XXX: Here we can use directly `cp` and `pip` because the rootfs of
#       the container is located in
#       /var/lib/docker/devicemapper/mnt/<ID>/rootfs/.
ssh $host "dockerctl copy dist/${wheel} nailgun:/root/"
ssh $host "dockerctl shell nailgun pip install -U ${wheel}"
ssh $host "docker restart fuel-core-6.1-nailgun"
