#!/bin/bash -ex

host=${1:-"cz5545-fuel"}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}

remote="$(git remote -v | awk "/$host/ && /fetch/{print \$2}")"
location="${remote#ssh://$host}/octane_nailgun"

git push --force $host HEAD

ssh $host \
    "set -ex;" \
    "cd ${location};" \
    "git reset --hard $branch;" \
    "git clean -x -d -f;" \
    "python setup.py bdist_wheel;" \
    "docker build -t octane/nailgun_6.1 .;" \
