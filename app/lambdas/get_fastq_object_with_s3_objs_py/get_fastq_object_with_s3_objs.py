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
import typing
from typing import Dict, TypedDict, List, Union
from boto3 import client
from urllib.parse import urlparse

# Layer imports
from orcabus_api_tools.fastq import get_fastq
from orcabus_api_tools.fastq.models import Fastq

# For debugging help
if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


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

    file_size_in_bytes = s3_client.head_object(
        Bucket=s3_obj.netloc,
        Key=s3_obj.path.lstrip('/')
    )['ContentLength']

    return int(file_size_in_bytes / (2 ** 30))


def handler(event, context) -> Dict[str, Union[str, List[S3Obj], Fastq, int]]:
    """
    Given a fastq id, collect the fastq object with s3 uris,
    :param event:
    :param context:
    :return:
    """
    fastq_id = event['fastqId']

    fastq_obj = get_fastq(fastq_id, includeS3Details=True)

    s3_objs: List[S3Obj] = [
        fastq_obj["readSet"]["r1"],
    ]

    if fastq_obj["readSet"].get("r2", None):
        s3_objs.append(fastq_obj["readSet"]["r2"])

    # Get the ephemeral storage size in GiB
    ephemeral_storage_size = sum(list(map(
        lambda s3_obj_iter: get_s3_file_size_in_gib(s3_obj_iter["s3Uri"]),
        s3_objs
    )))

    # Add 1 GiB buffer
    ephemeral_storage_size += 1

    return {
        "fastqId": fastq_id,
        "fastqObj": fastq_obj,
        "s3Objs": s3_objs,
        "ephemeralStorageSizeInGib": ephemeral_storage_size
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
