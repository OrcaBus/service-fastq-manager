#!/usr/bin/env python3

"""
Update fastq object

Given either an ntsm value, file compression information, or qc stats, call the PATCH API endpoint to update the fastq object.

"""

# Standard imports
from typing import Dict

# Orcabus imports
from orcabus_api_tools.fastq import (
    add_qc_stats,
    add_file_compression_information,
    add_ntsm_storage_object,
    add_read_count,
)
from orcabus_api_tools.fastq.models import Fastq


def handler(event, context) -> Dict[str, Fastq]:
    """
    Add fastq object depending on the input parameters.
    :param event:
    :param context:
    :return:
    """
    # Get the fastq id
    fastq_id = event.get("fastqId")

    if event.get("qc") is not None:
        fastq_obj = add_qc_stats(
            fastq_id, event.get("qc")
        )
    elif event.get("fileCompressionInformation") is not None:
        fastq_obj = add_file_compression_information(
            fastq_id, event.get("fileCompressionInformation")
        )
    elif event.get("ntsm") is not None:
        fastq_obj = add_ntsm_storage_object(
            fastq_id, event.get("ntsm")
        )
    elif event.get("readCount") is not None:
        fastq_obj = add_read_count(
            fastq_id, event.get("readCount")
        )
    else:
        raise ValueError("No valid parameters provided")

    return {
        "fastqObj": fastq_obj
    }


# if __name__ == "__main__":
#     from os import environ
#     environ['AWS_PROFILE'] = 'umccr-development'
#     environ['AWS_REGION'] = 'ap-southeast-2'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(handler(
#         {
#             "fastqId": "fqr.01JQ3BEPXTCR45FC976CX42FGM",
#             "ntsm": {
#                 "s3Uri": "s3://ntsm-fingerprints-843407916570-ap-southeast-2/ntsm/year=2025/month=03/day=24/9b773f7c-c204-4cdf-8825-3c31665cea9f/fqr.01JQ3BEPXTCR45FC976CX42FGM.ntsm"
#             },
#         },
#         None
#     )))



# if __name__ == "__main__":
#     from os import environ
#     environ['AWS_PROFILE'] = 'umccr-development'
#     environ['AWS_REGION'] = 'ap-southeast-2'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(handler(
#         {
#             "fastqId": "fqr.01JQ3BETTR9JPV33S3ZXB18HBN",
#             "fileCompressionInformation": {
#                 "r1GzipCompressionSizeInBytes": 43994124948,
#                 "r2GzipCompressionSizeInBytes": 46854233741,
#                 "r1RawMd5sum": "b2ce15279be6d00b2d5ab503602801f9",  # pragma: allowlist secret
#                 "r2RawMd5sum": "e060ed8955cbd12c594a64fd38c99a4c",  # pragma: allowlist secret
#                 "compressionFormat": "ORA"
#             }
#         },
#         None
#     )))
