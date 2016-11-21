#!/bin/bash

STORE_PATH=$1
SCRIPT=`readlink -f $0`
DIR=`dirname ${SCRIPT}`


CINDER_HOST=`bash ${DIR}/fetch_puppet_resource_param.sh cinder_config DEFAULT/host value`

if [[ -z ${CINDER_HOST} ]]; then
  CINDER_HOST=`bash ${DIR}/fetch_puppet_resource_param.sh cinder_config RBD-backend/backend_host value`
fi

CINDER_BACKEND=`bash ${DIR}/fetch_puppet_resource_param.sh cinder_config RBD-backend/volume_backend_name value`

echo "export NEW_HOST=\"${CINDER_HOST}#${CINDER_BACKEND}\"" > ${STORE_PATH}
