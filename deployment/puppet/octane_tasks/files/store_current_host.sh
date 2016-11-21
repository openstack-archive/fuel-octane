#!/bin/bash

STORE_PATH=$1
SCRIPT=`readlink -f $0`
DIR=`dirname ${SCRIPT}`


CINDER_HOST=`bash ${DIR}/fetch_puppet_resource_param.sh cinder_config DEFAULT/host value`
CINDER_BACKEND=`bash ${DIR}/fetch_puppet_resource_param.sh cinder_config DEFAULT/volume_backend_name value`

echo "export CURRENT_HOST=\"${CINDER_HOST}#${CINDER_BACKEND}\"" > ${STORE_PATH}
