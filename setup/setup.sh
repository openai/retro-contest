#!/bin/sh

cd `dirname $0`
if [ -d ../.git ]; then
    git submodule update --init --recursive
fi

docker build -f Dockerfile.compo-env -t compo-env ..
docker build -f Dockerfile.remote-env-bare -t remote-env:bare ..
docker build -f Dockerfile.remote-env -t remote-env ..
docker volume create --driver local \
    --opt type=tmpfs \
    --opt device=tmpfs \
    compo-tmp-vol
