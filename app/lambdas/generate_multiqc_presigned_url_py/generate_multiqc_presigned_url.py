#!/usr/bin/env python3

"""
Generate a presigned url for a MultiQC report in an S3 bucket.
"""

# Imports
import typing
import boto3
from urllib.parse import urlparse


if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def get_s3_client() -> 'S3Client':
    return boto3.client('s3')


def handler(events, context):
    """
    Import a MultiQC report from an S3 bucket and generate a presigned URL for it.
    :param events:
    :param context:
    :return:
    """

    # Get the report URI from the events
    report_uri = events.get("reportUri")

    report_obj = urlparse(report_uri)

    # Extract bucket name and object key from the report URI
    bucket_name = report_obj.netloc
    object_key = report_obj.path.lstrip('/')

    s3_client = get_s3_client()

    return s3_client.generate_presigned_url(
        'get_object',
        {
            "Bucket": bucket_name,
            "Key": object_key,
        }
    )
