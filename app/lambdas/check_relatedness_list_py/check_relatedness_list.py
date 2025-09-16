#!/usr/bin/env python3

"""
Check relatedness over a list of files

Input:
- relatednessList is a list of objects with the following attributes:
  * fastqListRowIdA: The ID of the first FASTQ pair
    fastqListRowIdB: The ID of the second FASTQ pair
    relatedness: The relatedness value between the two FASTQ pairs

Returns a dictionary with the following keys:
  related: A boolean indicating if all pairs are considered to be the 'same sample'
"""

# Standard library imports
from typing import Dict, List, Optional

# Set up logging
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def handler(event, context) -> Dict[str, Optional[bool]]:
    """
    Check relatedness over a list of files
    :param event:
    :param context:
    :return:
    """

    # Get relatednessList from the event
    relatedness_list: List[Dict[str, str]] = event['relatednessList']

    # Check if relatednessList is empty
    if len(relatedness_list) == 0:
        logger.error("Error, relatednessList is empty")
        return {
            "related": None
        }

    # Check if any are 'undetermined'
    if any(
            map(
                lambda relatedness_obj_iter_: relatedness_obj_iter_['undetermined'],
                relatedness_list
            )
    ):
        logger.error("Error, relatedness is undetermined in at least one sample")
        return {
            "related": None
        }

    # Check over the relatednessList
    unrelated_pairs = list(filter(
        lambda relatedness_obj_iter_: relatedness_obj_iter_['sameSample'] == False,
        relatedness_list
    ))

    related_pairs = list(filter(
        lambda relatedness_obj_iter_: relatedness_obj_iter_['sameSample'] == True,
        relatedness_list
    ))

    if len(related_pairs) == len(relatedness_list):
        return {
            "related": True
        }

    if len(unrelated_pairs) > 0:
        logger.info("Found unrelated pairs")
        for unrelated_pair in unrelated_pairs:
            logger.info(
                f"Unrelated pair: '{unrelated_pair['fastqIdA']}' & '{unrelated_pair['fastqIdB']}'")
        return {
            "related": False
        }


    # One pairing must not have had sufficient coverage
    return {
        "related": None
    }
