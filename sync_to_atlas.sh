#!/bin/bash
set -a
source ~/Tipjarprivate/.env
set +a
echo "Dumping..."
docker exec tipjarprivate-mongo-1 mongodump --db tipjar --archive > /tmp/tipjar.archive
echo "Restoring to Atlas..."
mongorestore --uri="$ATLAS_URI" --archive=/tmp/tipjar.archive --drop || \
docker run --rm -v /tmp/tipjar.archive:/tmp/tipjar.archive mongo:7 mongorestore --uri="$ATLAS_URI" --archive=/tmp/tipjar.archive --drop
echo "Synced $(date)"
