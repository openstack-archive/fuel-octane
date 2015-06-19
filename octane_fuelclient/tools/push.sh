#!/bin/bash -ex

host=${1:-"cz5545-fuel"}
branch=${2:-$(git rev-parse --abbrev-ref HEAD)}

remote="$(git remote -v | awk "/$host/ && /fetch/{print \$2}")"
location="${remote#ssh://$host}"

git push --force "$host" "$branch"

ssh $host \
    "set -ex;" \
    "cd ${location};" \
    "git reset --hard $branch;" \
    "git clean -x -d -f;" \
    "pip install -U ${location}/octane_fuelclient;"
