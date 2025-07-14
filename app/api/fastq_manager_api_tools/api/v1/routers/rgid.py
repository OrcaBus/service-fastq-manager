#!/usr/bin/env python3

"""
Some shortcut routes for getting the fastq object from the rgid
"""

# Standard imports
from typing import Optional
from fastapi import Depends, Query
from fastapi.routing import APIRouter, HTTPException
from dyntastic import A

# Model imports
from ....models.fastq import (
    FastqData, FastqResponseDict
)
from ....utils import sanitise_rgid

router = APIRouter()

# Get a fastq from orcabus id
@router.get(
    "/{rgid}",
    tags=["rgid query"],
    description="Get a Fastq Object by its rgid (index.lane.instrument_run_id) / (CCGCGGTT+CTAGCGCT.2.241024_A00130_0336_BHW7MVDSXC)"
)
async def get_fastq_from_rgid(
        rgid: str = Depends(sanitise_rgid),
        # Include s3 uri - resolve the s3 uri if requested
        include_s3_details: Optional[bool] = Query(
            default=False,
            alias="includeS3Details",
            description="Include the s3 details such as s3 uri and storage class"
        ),
) -> Optional[FastqResponseDict]:
    query_response = list(FastqData.query(
        A.rgid_ext == rgid,
        index="rgid_ext-index",
        load_full_item=True
    ))

    # If no results, return None
    if len(query_response) == 0:
        return None

    if len(query_response) > 1:
        # Return a 409 Conflict if the fastq already exists
        raise HTTPException(
            status_code=409,
            detail=f"Got multiple fastq rows for the same rgid {rgid}, This is not allowed."
        )

    # Get the first item from the query response
    fastq_id = query_response[0].id

    # Get the full fastq row data
    return FastqData.get(fastq_id).to_dict(
        include_s3_details=include_s3_details
    )
