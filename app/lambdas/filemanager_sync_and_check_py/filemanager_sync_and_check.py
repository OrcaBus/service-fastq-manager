#!/usr/bin/env python3

"""
Run filemanager sync and check if files exist in the filemanager
"""


# Local imports
from orcabus_api_tools.filemanager import (
    crawl_filemanager_sync,
    get_ingest_id_from_s3_uri,
)


def handler(event, context):
    """
    Sync filemanager at prefix and check if all files exist
    :param event:
    :param context:
    :return:
    """

    # Inputs
    if 'bucket' not in event:
        raise KeyError("Missing required field 'bucket' in event")
    if 'keys' not in event:
        raise KeyError("Missing required field 'keys' in event")
    if 'prefix' not in event:
        raise KeyError("Missing required field 'prefix' in event")

    bucket = event['bucket']
    keys = event['keys']
    prefix = event['prefix']

    if not keys:
        raise ValueError("'keys' must be a non-empty list")

    # Run crawl filemanager sync
    crawl_filemanager_sync(
        bucket=bucket,
        prefix=prefix
    )

    # Check if each key exists in the filemanager
    ingest_ids = {}
    for key in keys:
        s3_uri = f"s3://{bucket}/{key}"
        try:
            ingest_id = get_ingest_id_from_s3_uri(s3_uri)
            ingest_ids[key] = ingest_id
        except Exception:
            # Key not found in filemanager, skip
            pass

    return {
        "allFilesExist": len(ingest_ids) == len(keys),
        "ingestIds": ingest_ids
    }
