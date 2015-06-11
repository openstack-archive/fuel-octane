#!/bin/bash -ex

host=${1:-"cz5545-fuel"}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}

version=$(awk -F\" '/version/{print $2}' < setup.py)
wheel="octane_nailgun-${version}-py2-none-any.whl"

remote="$(git remote -v | awk "/$host/ && /fetch/{print \$2}")"
location="${remote#ssh://$host}/octane_nailgun"
container="fuel-core-6.1-nailgun"

git push --force "$host" "$branch"

ssh $host "set -ex;" \
          "cd ${location};" \
          "git reset --hard $branch;" \
          "git clean -x -d -f;" \
          "python setup.py bdist_wheel;" \
          "dockerctl copy ${location}/dist/${wheel} nailgun:/root/${wheel};" \
          "docker exec ${container} pip install -U ${wheel};" \
          "id=\"\$(docker inspect -f='{{if .ID}}{{.ID}}{{else}}{{.Id}}{{end}}' ${container})\";" \
          "rootfs=\"/var/lib/docker/devicemapper/mnt/\${id}/rootfs\";" \
          "patch -bV numbered -Np1 -d \"\${rootfs}\" < ${location}/tools/urls.py.patch ||:;" \
          "dockerctl shell ${container} pkill -f wsgi;"
