#!/usr/bin/env python3

from orcabus_api_tools.fastq import add_somalier_fingerprint

def handler(event, context):
    """
    Get FastqSet object from event and update its attributes.
    :param event:
    :param context:
    :return:
    """
    # Get inputs
    fastq_set_id = event['fastqSetId']
    somalier_uri = event['somalierUri']

    # Add somalier storage object
    add_somalier_fingerprint(
        fastq_set_id=fastq_set_id,
        s3_uri=somalier_uri
    )
