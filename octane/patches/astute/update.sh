#!/bin/sh -ex

. ${LIBPATH}/patch.sh

COMPONENT="astute"
SRC_PATH="/usr/lib64/ruby/gems/2.1.0/gems/astute-6.1.0/lib/astute"

dockerctl restart ${COMPONENT}
sleep 10
docker_patchfile ${COMPONENT}:${SRC_PATH}/deploy_actions.rb \
    ${PATCH_DIR}/${COMPONENT}/deploy_actions.rb.patch
sleep 5
dockerctl shell ${COMPONENT} supervisorctl restart ${COMPONENT}
