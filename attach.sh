#!/bin/bash

export NVIDIA_DOCKER=${NVIDIA_DOCKER:-"nvidia-docker"}
export COMPO_RESULTS=$(realpath $(dirname -- $0))/results

mkdir -p $COMPO_RESULTS

alias \
    docker-retro-contest-agent="\$NVIDIA_DOCKER run --rm -v compo-tmp-vol:/root/compo/tmp agent retro-contest-agent" \
    docker-retro-contest-remote="docker run --rm -v compo-tmp-vol:/root/compo/tmp -v \$COMPO_RESULTS:/root/compo/results remote-env retro-contest-remote"
