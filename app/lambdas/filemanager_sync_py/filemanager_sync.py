#!/usr/bin/env python3

"""
Run filemanager sync after uploading
"""


# Local imports
from orcabus_api_tools.filemanager import crawl_filemanager_sync


def handler(event, context):
    """
    Sync filemanager at prefix
    :param event:
    :param context:
    :return:
    """

    # Inputs
    bucket = event['bucket']
    prefix = event['prefix']

    # Run crawl filemanager sync
    crawl_filemanager_sync(
        bucket=bucket,
        prefix=prefix
    )
