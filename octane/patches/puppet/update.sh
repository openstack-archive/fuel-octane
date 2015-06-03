#!/bin/bash -ex
PATCH_DIR=$(dirname `readlink -f $0`)
. $PATCH_DIR/../../lib/patch
PUPPET_PATH="/etc/puppet/2014.2.2-6.1/modules"

pushd $PUPPET_PATH
find $PATCH_DIR -maxdepth 1 -mindepth 1 -type d \
    | xargs -I{} bash -c "patch -Np3 < {}/patch"
popd
