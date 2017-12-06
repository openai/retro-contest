#!/bin/bash

export NVIDIA_DOCKER=${NVIDIA_DOCKER:-"nvidia-docker"}

alias \
    docker-compo-env="\$NVIDIA_DOCKER run -tiv compo-tmp-vol:/root/compo/tmp compo-env" \
    docker-remote-env="docker run -tiv compo-tmp-vol:/root/compo/tmp remote-env"
