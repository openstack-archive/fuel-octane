docker_patch() {
    local CONTAINER=$1

    test -d ../docker/${CONTAINER} || {
        echo "${CONTAINER} invalid argument"
        return 1
    } 

    cp /usr/bin/patch ../docker/${CONTAINER}/resources/
    tag=`grep -Eim1 ^from ../docker/${CONTAINER}/Dockerfile | awk '{print $2 "_upgrade"}'`
    docker build -t "${tag}" ../docker/${CONTAINER}
} 
