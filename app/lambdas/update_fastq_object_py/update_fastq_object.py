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


# if __name__ == "__main__":
#     from os import environ
#     import json
#
#     environ['AWS_PROFILE'] = 'umccr-development'
#     environ['AWS_REGION'] = 'ap-southeast-2'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(handler(
#         {
#             "fastqId": "fqr.01JQ3BEKS05C74XWT5PYED6KV5",
#             "qc": {
#                 "insertSizeEstimate": 286,
#                 "rawWgsCoverageEstimate": 61.65,
#                 "r1Q20Fraction": 0,
#                 "r2Q20Fraction": 0,
#                 "r1GcFraction": 0.4,
#                 "r2GcFraction": 0.41,
#                 "duplicationFractionEstimate": 0.12,
#                 "sequaliReports": {
#                     "sequaliHtml": {
#                         "s3Uri": "s3://fastq-manager-sequali-outputs-843407916570-ap-southeast-2/sequali-html/year=2025/month=07/day=17/cfc96102-950b-4ddb-bb05-4b10e2399300/fqr.01JQ3BEKS05C74XWT5PYED6KV5.html"
#                     },
#                     "sequaliParquet": {
#                         "s3Uri": "s3://fastq-manager-sequali-outputs-843407916570-ap-southeast-2/sequali-parquet/year=2025/month=07/day=17/cfc96102-950b-4ddb-bb05-4b10e2399300/fqr.01JQ3BEKS05C74XWT5PYED6KV5.parquet"
#                     },
#                     "multiqcHtml": {
#                         "s3Uri": "s3://fastq-manager-sequali-outputs-843407916570-ap-southeast-2/multiqc-html/year=2025/month=07/day=17/cfc96102-950b-4ddb-bb05-4b10e2399300/fqr.01JQ3BEKS05C74XWT5PYED6KV5.html"
#                     },
#                     "multiqcParquet": {
#                         "s3Uri": "s3://fastq-manager-sequali-outputs-843407916570-ap-southeast-2/multiqc-parquet/year=2025/month=07/day=17/cfc96102-950b-4ddb-bb05-4b10e2399300/fqr.01JQ3BEKS05C74XWT5PYED6KV5.parquet"
#                     }
#                 }
#             }
#         },
#         None
#     )))
#
#     # {
#     #   "fastqObj": {
#     #     "id": "fqr.01JQ3BEKS05C74XWT5PYED6KV5",
#     #     "fastqSetId": "fqs.01JQ3BEKVEQGYVQNDVP4YQA7ZQ",
#     #     "index": "CCGCGGTT+CTAGCGCT",
#     #     "lane": 2,
#     #     "instrumentRunId": "241024_A00130_0336_BHW7MVDSXC",
#     #     "library": {
#     #       "orcabusId": "lib.01JBB5Y3901PA0X3FBMWBKYNMB",
#     #       "libraryId": "L2401538"
#     #     },
#     #     "platform": "Illumina",
#     #     "center": "UMCCR",
#     #     "date": "2024-10-24T00:00:00",
#     #     "readSet": {
#     #       "r1": {
#     #         "ingestId": "0197614c-8b68-7ef2-af73-10421d57501b",
#     #         "gzipCompressionSizeInBytes": 51816861806,
#     #         "rawMd5sum": "66804083d7972087f7717ea085c3a1b8"  # pragma: allowlist secret
#     #       },
#     #       "r2": {
#     #         "ingestId": "0197614c-c0cf-7cd0-8ec4-4ed6b3d43752",
#     #         "gzipCompressionSizeInBytes": 55505497747,
#     #         "rawMd5sum": "7048ceefbc53cbf37d44351e1b2f39eb"  # pragma: allowlist secret
#     #       },
#     #       "compressionFormat": "ORA"
#     #     },
#     #     "qc": {
#     #       "insertSizeEstimate": 286.0,
#     #       "rawWgsCoverageEstimate": 61.65,
#     #       "r1Q20Fraction": 0.0,
#     #       "r2Q20Fraction": 0.0,
#     #       "r1GcFraction": 0.4,
#     #       "r2GcFraction": 0.41,
#     #       "duplicationFractionEstimate": 0.12,
#     #       "sequaliReports": {
#     #         "sequaliHtml": {
#     #           "ingestId": "019816ed-f52c-7703-8af0-8afd1cb195f0"
#     #         },
#     #         "sequaliParquet": {
#     #           "ingestId": "019816ed-f319-7db3-a0c4-4cbdb5ac9f99"
#     #         },
#     #         "multiqcHtml": {
#     #           "ingestId": "019816ee-1732-7192-9854-7393e3ce7072"
#     #         },
#     #         "multiqcParquet": {
#     #           "ingestId": "019816ee-1b57-7e21-bf20-b094cb032f14"
#     #         }
#     #       }
#     #     },
#     #     "ntsm": null,
#     #     "readCount": 632745128,
#     #     "baseCountEst": 191089028656,
#     #     "isValid": true
#     #   }
#     # }
