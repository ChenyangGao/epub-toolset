#!/bin/bash

PROJDIR=`dirname "$0"`
PROJNAME=`basename ${PROJDIR}`
CURDIR=`pwd`
VERSION=`head -1 ${PROJDIR}/VERSION || echo latest`

function createpack() {
    local file=$1/${PROJNAME}_${VERSION}.pyz
    if /usr/bin/env python3 -m zipapp --compress ${PROJDIR}/${PROJNAME} --output ${file}
    then
        echo "Create a package file located in \n\t${file}"
    else
        return 1
    fi
}

createpack ${CURDIR} || createpack ${HOME} || createpack ${PROJDIR} || echo Cannot create package file
