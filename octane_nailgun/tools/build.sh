#!/bin/bash -ex

host=${1:-"cz5545-fuel"}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}

version=$(awk -F\" '/version/{print $2}' < setup.py)
wheel="octane_nailgun-${version}-py2-none-any.whl"

location="octane/octane_nailgun"
container="fuel-core-6.1-nailgun"

git push --force $host HEAD

ssh $host "cd ${location}; git reset --hard $branch"
ssh $host "cd ${location}; git clean -x -d -f"
ssh $host "cd ${location}; python setup.py bdist_wheel"
ssh $host "cd ${location}; docker build -t octane/nailgun_6.1 ."
