#!/bin/sh

cd `dirname $0`
if [ -d ../.git ]; then
    git submodule update --init --recursive
fi

docker build -f agent.docker -t agent ..
docker build -f agent-tf.docker -t agent:tensorflow-1.4 ..
docker build -f agent-pytorch.docker -t agent:pytorch-3.0 ..
docker build -f remote-env-0.docker -t remote-env:bare ..
docker build -f remote-env-1.docker -t remote-env ..
docker volume create --driver local \
    --opt type=tmpfs \
    --opt device=tmpfs \
    compo-tmp-vol
