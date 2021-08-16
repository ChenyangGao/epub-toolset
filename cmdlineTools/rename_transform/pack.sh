#!/bin/sh
PROJDIR=`dirname "$0"`
CURDIR=`pwd`

if [ -f $PROJDIR/VERSION ]
then
    VERSION=`cat $PROJDIR/VERSION`
else
    VERSION=latest
fi

function createpack() {
    local file=$1/rename_transform_$VERSION.pyz
    if /usr/bin/env python3 -m zipapp --compress $PROJDIR/rename_transform --output $file
    then
        echo "Create a package file located in \n\t$file"
    else
        return 1
    fi
}

createpack $CURDIR || createpack $HOME || createpack $PROJDIR || echo Cannot create package file
