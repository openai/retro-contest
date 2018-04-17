#!/bin/sh

cd `dirname $0`
if [ -d ../.git ]; then
    git submodule update --init --recursive
fi

echo - Pulling base images
docker pull -a openai/retro-agent
docker pull -a openai/retro-env
if [ "$1" = "rebuild" ]; then
	echo - Building base CUDA images
	docker build --pull -f agent.docker -t openai/retro-agent:bare-cuda8 --build-arg CUDA=8.0 --build-arg CUDNN=6 --cache-from openai/retro-agent:bare-cuda8 ..
	docker build --pull -f agent.docker -t openai/retro-agent:bare-cuda9 --build-arg CUDA=9.0 --build-arg CUDNN=7 --cache-from openai/retro-agent:bare-cuda9 ..
	echo - Building base TensorFlow images
	docker build -t openai/retro-agent:tensorflow-1.4 --build-arg CUDA=8 --build-arg TF=1.4.1 --cache-from openai/retro-agent:tensorflow-1.4 - < agent-tf.docker
	docker build -t openai/retro-agent:tensorflow-1.7 --build-arg CUDA=9 --build-arg TF=1.7.0 --cache-from openai/retro-agent:tensorflow-1.7 - < agent-tf.docker
	echo - Building base PyTorch images
	docker build -t openai/retro-agent:pytorch --cache-from openai/retro-agent:pytorch - < agent-pytorch.docker
	echo - Building remote image
	docker build -f remote-env-0.docker -t openai/retro-env --cache-from openai/retro-env ..
fi
if [ -n "$(ls ../roms)" ]; then
	echo - Building remote image with ROMs
	docker build -f remote-env-1.docker -t openai/retro-env ..
fi
echo - Tagging images
docker tag openai/retro-agent:tensorflow-1.7 openai/retro-agent:tensorflow
docker tag openai/retro-agent:tensorflow openai/retro-agent:latest
docker tag openai/retro-agent agent

echo - Installing Python library
pip3 install -e '../support[docker,rest]'
