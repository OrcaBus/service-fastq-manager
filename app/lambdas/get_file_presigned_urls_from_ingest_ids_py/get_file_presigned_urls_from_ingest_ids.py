#!/usr/bin/env python3

"""
Given a list of ingest ids, perform the following:

1. Call the file manager to get presigned urls for each ingest id

2. Download the files from the presigned urls

3. Run MultiQC on the downloaded files

4. Upload the MultiQC report to the fastq cache bucket
"""

# Standard library imports
from orcabus_api_tools.filemanager import get_presigned_urls_from_ingest_ids
import logging

# Get logger
logger = logging.getLogger(__name__)


def handler(event, context):
    """
    Lambda handler function to process MultiQC reports.
    :param event:
    :param context:
    :return:
    """

    # Get the ingest id list from the event
    ingest_id_list = event.get("ingestIdList")

    # Step 1: Get presigned URLs for the ingest IDs
    logger.info("Get presigned URLs for ingest IDs")
    presigned_url_list = list(map(
        lambda presigned_url_dict_iter_: presigned_url_dict_iter_["presignedUrl"],
        get_presigned_urls_from_ingest_ids(ingest_id_list)
    ))

    # Generate a presigned url for the multiqc report
    return {
        "presignedUrlList": presigned_url_list
    }


# if __name__ == "__main__":
#     from os import environ
#
#     environ['AWS_PROFILE'] = 'umccr-development'
#     environ['AWS_REGION'] = 'ap-southeast-2'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     # Test the handler function with a sample event
#     print(
#         json.dumps(
#             handler(
#                 {
#                     "ingestIdList": [
#                         "019816ee-1b57-7e21-bf20-b094cb032f14"
#                     ]
#                 },
#                 None
#             ),
#             indent=2,
#         )
#     )
#
#     # {
#     #   "presignedUrlList": [
#     #     "https://fastq-manager-sequali-outputs..."
#     #   ]
#     # }
