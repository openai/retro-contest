#!/bin/sh

cd `dirname $0`
if [ -d ../.git ]; then
    git submodule update --init --recursive
fi

docker build --pull -f agent.docker -t openai/retro-agent:bare-cuda8 --build-arg CUDA=8.0-cudnn6 --cache-from openai/retro-agent:bare-cuda8 .. && \
docker build --pull -f agent.docker -t openai/retro-agent:bare-cuda9 --build-arg CUDA=9.0-cudnn7 --cache-from openai/retro-agent:bare-cuda9 .. && \
docker build -f agent-tf.docker -t openai/retro-agent:tensorflow-1.4 --build-arg CUDA=8 --build-arg TF=1.4.1 --cache-from openai/retro-agent:tensorflow-1.4 .. && \
docker build -f agent-tf.docker -t openai/retro-agent:tensorflow-1.7 --build-arg CUDA=9 --build-arg TF=1.7.0 --cache-from openai/retro-agent:tensorflow-1.7 .. && \
docker build -f agent-pytorch.docker -t openai/retro-agent:pytorch --cache-from openai/retro-agent:pytorch .. && \
docker build -f remote-env-0.docker -t openai/retro-env --cache-from openai/retro-env .. && \
docker build -f remote-env-1.docker -t remote-env ..
docker tag openai/retro-agent:tensorflow-1.7 openai/retro-agent:tensorflow
docker tag openai/retro-agent:tensorflow openai/retro-agent:latest
docker tag openai/retro-agent:latest agent
docker tag openai/retro-env remote-env:bare
