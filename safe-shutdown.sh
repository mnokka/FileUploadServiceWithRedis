#!/bin/bash

set -e

VOLUME_PATH="/media/mika/e821e31d-8af3-4cd0-9fef-a5a11faa8b8e1/VOLUMES/FILEUPLOAD2/REDIS/dump.rdb"

echo "🔄 Requesting Redis to save current data to disk..."
docker exec images_redis redis-cli save

echo "✅ Data saved. Taking down docker-compose services..."
docker-compose down

if [ -f "$VOLUME_PATH" ]; then
    echo "📂 Redis dump found. Details:"
    ls -lh "$VOLUME_PATH"
else
    echo "⚠️ WARNING: Redis dump file not found after shutdown! Check volumes!"
fi

echo "🚀 Shutdown process complete."
