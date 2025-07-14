#!/usr/bin/env python

import typing
from typing import Dict
from datetime import datetime

if typing.TYPE_CHECKING:
    from orcabus_api_tools.filemanager.models import FileObject

S3_INGEST_ID_TO_OBJ_MAP_CACHE: Dict[str, 'FileObject'] = {}
S3_INGEST_ID_TO_OBJ_MAP_CACHE_TIMESTAMP: Dict[str, float] = {}

def update_cache(ingest_id: str, s3_obj: 'FileObject'):
    global S3_INGEST_ID_TO_OBJ_MAP_CACHE
    global S3_INGEST_ID_TO_OBJ_MAP_CACHE_TIMESTAMP
    S3_INGEST_ID_TO_OBJ_MAP_CACHE[ingest_id] = s3_obj
    S3_INGEST_ID_TO_OBJ_MAP_CACHE_TIMESTAMP[ingest_id] = datetime.now().timestamp()


def check_in_cache(ingest_id: str) -> bool:
    global S3_INGEST_ID_TO_OBJ_MAP_CACHE
    global S3_INGEST_ID_TO_OBJ_MAP_CACHE_TIMESTAMP
    if ingest_id not in S3_INGEST_ID_TO_OBJ_MAP_CACHE:
        return False
    # Check if the cache is older than 15 minutes
    if (S3_INGEST_ID_TO_OBJ_MAP_CACHE_TIMESTAMP[ingest_id] + 900 < datetime.now().timestamp()):
        # Remove the stale entry
        S3_INGEST_ID_TO_OBJ_MAP_CACHE.pop(ingest_id, None)
        S3_INGEST_ID_TO_OBJ_MAP_CACHE_TIMESTAMP.pop(ingest_id, None)

    return ingest_id in S3_INGEST_ID_TO_OBJ_MAP_CACHE


def get_from_cache(ingest_id: str) -> 'FileObject':
    global S3_INGEST_ID_TO_OBJ_MAP_CACHE
    return S3_INGEST_ID_TO_OBJ_MAP_CACHE.get(ingest_id, None)
