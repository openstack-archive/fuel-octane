#!/bin/bash -x

. ../lib/patch

PATCH_DIR=$(dirname $0)/../patches/

pushd $PATCH_DIR/astute
./update.sh
popd

pushd $PATCH_DIR/puppet
./update.sh
popd
