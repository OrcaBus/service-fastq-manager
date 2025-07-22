#!/usr/bin/env python3

"""
Generate a multiqc report for a set of fastq files
"""
# Standard imports
import json
from os import environ
from typing import List, Annotated, Optional
from fastapi import Depends, Body, Query
from fastapi.routing import APIRouter, HTTPException
from typing import cast

# API imports
from orcabus_api_tools.filemanager import (
    get_presigned_url_from_ingest_id,
)

# Util / global imports
from ....globals import MULTIQC_COLLECTOR_STEP_FUNCTION_ARN_ENV_VAR
from ....models.file_storage import FileStorageObjectCreate, FileStorageObjectData
from ....utils import get_sfn_client, sanitise_fqr_orcabus_id_list, sanitise_multiqc_job_id

# Model imports
from ....events.events import put_multiqc_job_update_event
from ....models.fastq import (
    FastqData
)
from ....models.multiqc import (
    MultiqcJobData,
    MultiqcJobResponseDict,
    MultiqcJobPatch,
    get_default_patch_multiqc_job_entry,
)

router = APIRouter()

# Get a multiqc report for a list of fastq files
@router.post(
    "",
    tags=["multiqc"],
    description="Generate a multiqc report for a set of fastq files",
)
async def generate_multiqc_report(
        fastq_id_list: List[str] = Depends(sanitise_fqr_orcabus_id_list),
        # FIXME add query - to combine library lanes?
) -> MultiqcJobResponseDict:
    fastq_data_response: List[FastqData] = list(FastqData.batch_get(
        fastq_id_list
    ))

    # Iterate each fastq data object and ensure that the qc.sequali_reports.multiqc_parquet is set
    missing_data_list = list(filter(
        lambda fastq_data_iter_: (
            not fastq_data_iter_.qc or
            not fastq_data_iter_.qc.sequali_reports or
            not fastq_data_iter_.qc.sequali_reports.multiqc_parquet
        ),
        fastq_data_response
    ))

    if len(missing_data_list) > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Missing multiqc parquet data for some fastq files, {list(map(lambda x: x['id'], missing_data_list))}",
        )

    multiqc_job_obj = MultiqcJobData.from_dict(
        fastq_id_list=fastq_id_list
    )

    # Save to DB before we start the job
    multiqc_job_obj.save()

    # Generate the multiqc report
    multiqc_job_obj.steps_execution_arn = get_sfn_client().start_execution(
        stateMachineArn=environ[MULTIQC_COLLECTOR_STEP_FUNCTION_ARN_ENV_VAR],
        input=json.dumps(
            {
                "jobId": multiqc_job_obj.id,
                "fastqIdList": fastq_id_list,
            }
        )
    )['executionArn']

    # Save the job to the database
    multiqc_job_obj.save()

    # Create dict
    multiqc_job_dict = multiqc_job_obj.to_dict()

    # Put event into the ethos
    put_multiqc_job_update_event(
        multiqc_response_object=multiqc_job_dict,
        event_status=multiqc_job_obj.status
    )

    # Return the multiqc job as a dictionary
    return multiqc_job_dict


# MODIFIED GETS
# Generate a presigned url of a multiqc report
@router.get(
    "/{multiqc_job_id}:presign",
    tags=["multiqc presign"],
    description="Get a presigned URL for a multiqc report job by its ID",
)
async def get_multiqc_report_presigned_url(
        multiqc_job_id: str = Depends(sanitise_multiqc_job_id)
) -> str:
    multiqc_job_obj = MultiqcJobData.get(multiqc_job_id)

    # Check if the job has succeeded
    if multiqc_job_obj.status != 'SUCCEEDED':
        raise HTTPException(
            status_code=400,
            detail=f"Multiqc report job {multiqc_job_id} has not succeeded yet."
        )

    # Return the presigned URL for the multiqc report
    # Generate a presigned URL for the multiqc report HTML file
    return get_presigned_url_from_ingest_id(multiqc_job_obj.multiqc_html.ingest_id)


# Query status of multiqc report job
@router.get(
    "/{multiqc_job_id}",
    tags=["multiqc get"],
    description="Get a multiqc report job by its ID",
)
async def get_multiqc_job(
        multiqc_job_id: str = Depends(sanitise_multiqc_job_id),
        include_s3_details: Optional[bool] = Query(
            default=False,
            alias="includeS3Details",
            description="Include the s3 details such as s3 uri and storage class"
        ),
) -> MultiqcJobResponseDict:
    multiqc_job_obj = MultiqcJobData.get(multiqc_job_id)

    # Return the multiqc job as a dictionary
    return multiqc_job_obj.to_dict(
        include_s3_details= include_s3_details
    )


# PATCHES
@router.patch(
    "/{multiqc_job_id}",
    tags=["multiqc update"],
    description="Update the job status of a multiqc report",
)
async def add_multiqc_job_status_update(
        multiqc_job_id: str = Depends(sanitise_multiqc_job_id),
        multiqc_job_information: Annotated[MultiqcJobPatch, Body()] = get_default_patch_multiqc_job_entry()
) -> MultiqcJobResponseDict:
    multiqc_job_obj = MultiqcJobData.get(multiqc_job_id)

    # Get the status of the job
    multiqc_job_obj.status = multiqc_job_information.status

    # If the job is succeeded, get the output uri
    if multiqc_job_obj.status == 'SUCCEEDED':
        multiqc_job_obj.multiqc_html = FileStorageObjectData(**dict(multiqc_job_information.multiqc_html.model_dump()))
        multiqc_job_obj.multiqc_parquet = FileStorageObjectData(**dict(multiqc_job_information.multiqc_parquet.model_dump()))

    # Save the job to the database
    multiqc_job_obj.save()

    # Create dict
    multiqc_job_dict = multiqc_job_obj.to_dict()

    # Put update event into the ethos
    put_multiqc_job_update_event(
        multiqc_response_object=multiqc_job_dict,
        event_status=multiqc_job_obj.status
    )

    # Return the fastq as a dictionary
    return multiqc_job_dict
