#!/bin/sh

SCRIPTDIR=`dirname $0`
if [ -d $SCRIPTDIR/../.git ]; then
    git submodule update --init --recursive
fi

docker build -f $SCRIPTDIR/Dockerfile.compo-env -t compo-env .
docker build -f $SCRIPTDIR/Dockerfile.remote-env -t remote-env .
docker volume create --driver local \
    --opt type=tmpfs \
    --opt device=tmpfs \
    compo-tmp-vol
