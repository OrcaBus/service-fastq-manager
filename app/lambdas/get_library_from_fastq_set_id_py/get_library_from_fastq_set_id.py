#!/usr/bin/env python3

"""
Given a fastq set id, get the library object
"""

# Layer Imports
from orcabus_api_tools.fastq import get_fastq_set
from orcabus_api_tools.metadata import get_library_from_library_orcabus_id


def handler(event, context):

    # Inputs
    fastq_set_id = event["fastqSetId"]

    # Get the library orcabus id
    library_orcabus_id = get_fastq_set(fastq_set_id)['library']['orcabusId']

    return {
        "libraryObj": get_library_from_library_orcabus_id(library_orcabus_id)
    }
