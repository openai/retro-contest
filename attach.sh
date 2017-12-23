#!/bin/bash

export NVIDIA_DOCKER=${NVIDIA_DOCKER:-"nvidia-docker"}
export COMPO_RESULTS=$(realpath $(dirname -- $0))/results

mkdir -p $COMPO_RESULTS

alias \
    docker-retro-challenge-agent="\$NVIDIA_DOCKER run --rm -v compo-tmp-vol:/root/compo/tmp agent retro-challenge-agent" \
    docker-retro-challenge-remote="docker run --rm -v compo-tmp-vol:/root/compo/tmp -v \$COMPO_RESULTS:/root/compo/results remote-env retro-challenge-remote"
