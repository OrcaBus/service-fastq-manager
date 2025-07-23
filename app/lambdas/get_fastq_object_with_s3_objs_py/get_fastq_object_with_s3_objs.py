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
from typing import Dict, TypedDict, List, Union

# Layer imports
from orcabus_api_tools.fastq import get_fastq

class S3Obj(TypedDict):
    ingestId: str
    s3Uri: str
    sha256: str
    storageClass: str


def handler(event, context) -> Dict[str, Union[str, List[S3Obj]]]:
    """
    Given a fastq id, collect the fastq object with s3 uris,
    :param event:
    :param context:
    :return:
    """
    fastq_id = event['fastqId']

    fastq_obj = get_fastq(fastq_id, includeS3Details=True)

    s3_objs = [
        fastq_obj["readSet"]["r1"],
    ]

    if fastq_obj["readSet"].get("r2", None):
        s3_objs.append(fastq_obj["readSet"]["r2"])

    return {
        "fastqId": fastq_id,
        "fastqObj": fastq_obj,
        "s3Objs": s3_objs,
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
