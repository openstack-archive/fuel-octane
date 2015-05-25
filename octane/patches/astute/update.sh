#!/bin/sh -ex

FUNCTIONS_PATH="$(dirname $0)/../../lib"
. ${FUNCTIONS_PATH}/patch

PATCH_DIR=$(dirname $0)
CONTAINER="astute"
SRC_PATH="/usr/lib64/ruby/gems/2.1.0/gems/astute-6.0.0/lib/astute/"

dockerctl restart ${CONTAINER}
sleep 10
patchfile ${CONTAINER}:${SRC_PATH}/deploy_actions.rb \
    ${PATCH_DIR}/deploy_actions.rb.patch
sleep 5
patchfile ${CONTAINER}:${SRC_PATH}/deploy_actions.rb \
    ${PATCH_DIR}/deploy_actions.rb.patch
dockerctl shell ${CONTAINER} restart ${CONTAINER}
