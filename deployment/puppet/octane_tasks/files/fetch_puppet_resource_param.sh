#!/bin/bash

PUPPET_TYPE=$1
RESOURCE_NAME=$2
RESOURCE_PARAM=$3

echo `puppet resource ${PUPPET_TYPE} ${RESOURCE_NAME} | grep ${RESOURCE_PARAM} | awk '{print $3}' | tr -d "',"`
