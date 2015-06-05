#!/bin/bash -ex

host=${1:-"cz5545-fuel"}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}

container="fuel-core-6.1-nailgun"
version=$(awk -F\" '/version/{print $2}' < setup.py)
wheel="octane_nailgun-${version}-py2-none-any.whl"

git push --force $host HEAD
# TODO: Next lines can be separated in independent script tnat can be
#       copied into $host and runned from there.
ssh $host "cd octane; git reset --hard $branch"
ssh $host "cd octane; git clean -x -d -f"
ssh $host "cd octane/octane_nailgun; python setup.py bdist_wheel"

ssh $host "docker cp ${container}:/root/ dist/${wheel}"
ssh $host "docker exec ${container} pip install -U ${wheel}"
ssh $host "docker restart ${container}"
