#!/usr/bin/env python3

"""
Given a fastq id, collect the fastq object with s3 uris,

Return a dictionary with the following keys:
{
  "fastqId": "fastqId",
  "s3UriList": ["s3Uri1", "s3Uri2", ...],
}
"""
# Standard library imports
import math
import typing
from typing import Dict, TypedDict, List, Union
from boto3 import client
from urllib.parse import urlparse
from botocore.exceptions import ClientError
import logging

# For debugging help
if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


# Setup logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Classes
class S3Obj(TypedDict):
    ingestId: str
    s3Uri: str
    sha256: str
    storageClass: str


def get_s3_file_size_in_gib(s3_uri: str) -> int:
    """
    Given an s3 uri, return the file size in GiB
    :param s3_uri:
    :return:
    """
    s3_obj = urlparse(s3_uri)
    s3_client: S3Client = client('s3')

    try:
        file_size_in_bytes = s3_client.head_object(
            Bucket=s3_obj.netloc,
            Key=s3_obj.path.lstrip('/')
        )['ContentLength']
    except ClientError:
        logger.warning("Could not get head object for s3 uri: %s", s3_uri)
        return -1

    # We have the file size in bytes, convert to GiB
    # Round up to the nearest GiB and add 1 GiB buffer
    return math.ceil(file_size_in_bytes / (2 ** 30))


def handler(event, context) -> Dict[str, int]:
    """
    Calculate the ephemeral storage size required for a list of s3 objects
    :param event:
    :param context:
    :return:
    """
    # S3 Objs
    s3_objs: List[S3Obj] = event.get("s3Objs", [])

    # Get the ephemeral storage size in GiB
    ephemeral_storage_size = sum(map(
        lambda s3_obj_iter: get_s3_file_size_in_gib(s3_obj_iter["s3Uri"]),
        s3_objs
    ))

    # Add 5 GiB buffer
    ephemeral_storage_size += 5

    # Must be at least 20 GiB
    ephemeral_storage_size = max(ephemeral_storage_size, 20)

    return {
        "ephemeralStorageSizeInGiB": ephemeral_storage_size
    }


# if __name__ == "__main__":
#     from os import environ
#     import json
#
#     environ['AWS_PROFILE'] = 'umccr-production'
#     environ['AWS_REGION'] = 'ap-southeast-2'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(
#         handler(
#             {
#                 "fastqId": "fqr.01JN26HNGR2RK042S3X58S1WSW"
#             },
#             None
#         ),
#         indent=4
#     ))
