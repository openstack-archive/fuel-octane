#!/bin/bash -ex

host=${1:-"cz5545-fuel"}
location=${2:-"/root/octane"}
branch=${3:-$(git rev-parse --abbrev-ref HEAD)}

ssh $host "yum install -y git;" \
          "pip install wheel;" \
          "mkdir -p ${location};" \
          "git init ${location};" \
          "git config --file ${location}/.git/config receive.denyCurrentBranch warn;"
git remote add "$host" "ssh://${host}${location}"
git push --force "$host" "$branch"
ssh $host "cd ${location};" \
          "git reset --hard $branch;"
