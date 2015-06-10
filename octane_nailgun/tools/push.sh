#!/bin/bash -ex

host=${1:-"cz5545-fuel"}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}

version=$(awk -F\" '/version/{print $2}' < setup.py)
wheel="octane_nailgun-${version}-py2-none-any.whl"

location="octane/octane_nailgun"
container="fuel-core-6.1-nailgun"

git push --force "$host" "$branch"

ssh $host "cd ${location}; git reset --hard $branch"
ssh $host "cd ${location}; git clean -x -d -f"

id=$(ssh $host "docker inspect -f='{{if .ID}}{{.ID}}{{else}}{{.Id}}{{end}}' ${container}")
rootfs="/var/lib/docker/devicemapper/mnt/${id}/rootfs"
ssh $host "patch -bV numbered -Np1 -d $rootfs < ${location}/tools/urls.py.patch || :"

ssh $host "cd ${location}; python setup.py bdist_wheel"

ssh $host "cd ${location}; dockerctl copy dist/${wheel} nailgun:/root/${wheel}"
ssh $host "docker exec ${container} pip install -U ${wheel}"
ssh $host "dockerctl shell ${container} pkill -f wsgi"
