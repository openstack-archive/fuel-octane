#!/bin/bash -x


octane_rpmbuild() {
    local WORK_DIR=$1
    (
        cd $WORK_DIR
        git clone https://github.com/Mirantis/octane.git
        mkdir BUILD RPMS SOURCES SPECS SRPMS
        (
            cd octane
            git archive --format=tar.gz -o ../SOURCES/octane.tar.gz master
            sed "s/%TMPDIR%/$1/g" /home/ryabin/spaces/rpm-build/octane.spec > octane.spec
        )
        #rm -rf octane
        rpmbuild --define "_topdir ${PWD}" -ba ./octane.spec
    ) 
} 

TMP_DIR=`mktemp -d /tmp/rpmbuild-octane.XXXXXX`

octane_rpmbuild $TMP_DIR
