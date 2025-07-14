#!/usr/bin/env python3

"""
Given a fastq set id, return the fastq list row objects that are in the fastq set

Inputs:
  * fastqSetId: The id of the fastq set to get the fastq list row objects for

Outputs:
  * fastqList: A list of FastqListRow objects that are in the fastq set

"""

# Standard imports
from typing import List, Dict

# Orcabus imports
from orcabus_api_tools.fastq import (
    get_fastq_set
)
from orcabus_api_tools.fastq.models import Fastq


def handler(event, context) -> Dict[str, List[Fastq]]:
    """

    :param event:
    :param context:
    :return:
    """
    fastq_set_id = event.get("fastqSetId")

    if not fastq_set_id:
        raise ValueError("fastqSetId is required")

    return {
        "fastqList": get_fastq_set(fastq_set_id, includeS3Details=True)['fastqSet']
    }
