#!/bin/bash

### your registry must have the following environment var set
# REGISTRY_STORAGE_DELETE_ENABLED=true
### replace YOUR_SERVER with corect info
REGISTRY_URL=https://YOUR_SERVER:5000
### host registry volume folder
REGISTRY_ROOT=/registry
### container to execute garbage-collect
CONTAINER_NAME=services_registry.1
### config file used by your registry
REG_CONFIG=/etc/docker/registry/config.yml
### number of most recent digests to keep
NUM_DIGEST_KEEP=3
### tag to check
TAG=latest

if ! [ -r $REGISTRY_ROOT ]; then
  echo registry root $REGISTRY_ROOT not readable
  exit;
fi

CONTAINER=`docker ps | grep $CONTAINER_NAME | cut -d' ' -f1`
if [ -z $CONTAINER ]; then
  echo container $CONTAINER_NAME not found
  exit 1
fi

for repo in `ls $REGISTRY_ROOT/docker/registry/v2/repositories` ; do
  echo $repo
  for hash in `ls $REGISTRY_ROOT/docker/registry/v2/repositories/$repo/_manifests/tags/$TAG/index/sha256 -t | tail -n +$NUM_DIGEST_KEEP`; do
    echo $hash
    curl -X DELETE $REGISTRY_URL/v2/$repo/manifests/sha256:$hash;
  done
done


docker exec $CONTAINER /bin/registry garbage-collect $REG_CONFIG
