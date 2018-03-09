#!/bin/bash

DATA_PATH=$(python -c 'import retro; print(retro.data_path(retro.RETRO_DATA_PATH))')
echo "Importing games from $DATA_PATH..."
CONTAINER_ID=$(docker run -v "$DATA_PATH":/root/roms:ro -d remote-env 'python /tmp/gym-retro/scripts/import.py /root/roms')
docker attach $CONTAINER_ID
docker commit $CONTAINER_ID remote-env:full
docker rm $CONTAINER_ID
