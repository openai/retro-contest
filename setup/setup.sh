#!/bin/sh

cd `dirname $0`
if [ -d ../.git ]; then
    git submodule update --init --recursive
fi

docker pull -a quay.io/openai/retro-agent
docker pull -a quay.io/openai/retro-env
docker build -f agent.docker -t quay.io/openai/retro-agent --cache-from quay.io/openai/retro-agent .. && \
docker build -f agent-tf.docker -t quay.io/openai/retro-agent:tensorflow --cache-from quay.io/openai/retro-agent:tensorflow .. && \
docker build -f agent-pytorch.docker -t quay.io/openai/retro-agent:pytorch --cache-from quay.io/openai/retro-agent:pytorch .. && \
docker build -f remote-env-0.docker -t quay.io/openai/retro-env --cache-from quay.io/openai/retro-env .. && \
docker build -f remote-env-1.docker -t quay.io/openai/retro-env-full --cache-from quay.io/openai/retro-env-full ..
docker tag quay.io/openai/retro-agent agent
docker tag quay.io/openai/retro-env remote-env:bare
docker tag quay.io/openai/retro-env-full remote-env
