#!/bin/sh

cd `dirname $0`
if [ -d ../.git ]; then
    git submodule update --init --recursive
fi

docker build -f agent.docker -t openai/retro-agent:bare --cache-from openai/retro-agent:bare .. && \
docker build -f agent-tf.docker -t openai/retro-agent:tensorflow --cache-from openai/retro-agent:tensorflow .. && \
docker build -f agent-pytorch.docker -t openai/retro-agent:pytorch --cache-from openai/retro-agent:pytorch .. && \
docker build -f remote-env-0.docker -t openai/retro-env --cache-from openai/retro-env .. && \
docker build -f remote-env-1.docker -t remote-env --cache-from openai/retro-env ..
docker tag openai/retro-agent:tensorflow openai/retro-agent:latest
docker tag openai/retro-agent:latest agent
docker tag openai/retro-env remote-env:bare
