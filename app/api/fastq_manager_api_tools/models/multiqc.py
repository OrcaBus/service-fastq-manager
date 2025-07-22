#!/usr/bin/env python3
from datetime import datetime, timezone
from os import environ
from typing import TypedDict, Literal, List, Optional, Self, NotRequired
from dyntastic import Dyntastic
from pydantic import BaseModel, ConfigDict, model_validator, Field

from orcabus_api_tools.filemanager import get_s3_objs_from_ingest_ids_map
# Local imports
from .file_storage import (
    FileStorageObjectResponseDict,
    FileStorageObjectData,
    FileStorageObjectResponse, FileStorageObjectCreate
)
from ..cache import check_in_cache, update_cache
from ..globals import MULTIQC_JOB_PREFIX
from ..utils import to_camel, get_ulid, to_snake


# Type aliases
MultiqcJobStatusType = Literal[
    "PENDING",
    "RUNNING",
    "FAILED",
    "ABORTED",
    "SUCCEEDED",
]


def get_default_patch_multiqc_job_entry() -> 'MultiqcJobPatch':
    return MultiqcJobPatch(**dict({"status": 'PENDING'}))


def default_start_time_factory() -> datetime:
    """
    Default factory for the start time of the job
    :return: The current datetime
    """
    return datetime.now(timezone.utc)


def default_job_id_factory() -> str:
    return f"{MULTIQC_JOB_PREFIX}.{get_ulid()}"


class MultiqcJobResponseDict(TypedDict):
    id: str  # The job id
    fastqIdList: List[str]  # List of FASTQ IDs associated with the job
    status: MultiqcJobStatusType  # The job status
    stepsExecutionArn: NotRequired[str]  # The execution ARN of the job steps function
    multiqcHtml: NotRequired[FileStorageObjectResponseDict]
    multiqcParquet: NotRequired[FileStorageObjectResponseDict]


class MultiqcJobBase(BaseModel):
    fastq_id_list: List[str] # List of FASTQ IDs associated with the job


class MultiqcJobOrcabusId(BaseModel):
    id: str = Field(default_factory=lambda: f"{MULTIQC_JOB_PREFIX}.{get_ulid()}")


class MultiqcJobWithOrcabusId(MultiqcJobBase, MultiqcJobOrcabusId):
    """
    Order class inheritance this way to ensure that the id field is set first
    """
    status: MultiqcJobStatusType = Field(default='PENDING')
    steps_execution_arn: Optional[str] = None  # The execution ARN of the job steps function
    multiqc_html: Optional[FileStorageObjectData] = None
    multiqc_parquet: Optional[FileStorageObjectData] = None


class MultiqcJobPatch(BaseModel):
    """
    The job patch object
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    status: MultiqcJobStatusType  # The job status
    steps_execution_arn: Optional[str] = None # The execution ARN of the job steps function
    multiqc_html: Optional[FileStorageObjectCreate] = None # The URI of the MultiQC output file
    multiqc_parquet: Optional[FileStorageObjectCreate] = None # The URI of the MultiQC output file


class MultiqcJobResponse(MultiqcJobWithOrcabusId):
    model_config = ConfigDict(
        alias_generator=to_camel
    )

    multiqc_html: Optional[FileStorageObjectResponse] = None
    multiqc_parquet: Optional[FileStorageObjectResponse] = None

    # Set keys to camel case
    @model_validator(mode='before')
    def convert_keys_to_camel(cls, values):
        return {to_camel(k): v for k, v in values.items()}

    # Set the model_dump method response
    def model_dump(self, **kwargs) -> MultiqcJobResponseDict:
        if 'by_alias' not in kwargs:
            kwargs['by_alias'] = True
        if 'exclude_none' not in kwargs:
            kwargs['exclude_none'] = True

        # Handle specific kwargs
        include_s3_details = False
        if 'include_s3_details' in kwargs:
            kwargs = kwargs.copy()
            include_s3_details = kwargs.pop('include_s3_details')

        # Complete recursive serialization manually
        data = super().model_dump(**kwargs)

        # Convert keys to camel case
        # Manually serialize the sub fields
        for field_name in [
            "multiqc_html",
            "multiqc_parquet",
        ]:
            field = getattr(self, field_name)
            if field is not None:
                data[to_camel(field_name)] = field.model_dump(
                    **kwargs, include_s3_details=include_s3_details
                )

        return data


class MultiqcJobCreate(MultiqcJobBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    def model_dump(self, **kwargs) -> 'MultiqcJobResponseDict':
        return (
            MultiqcJobResponse(**super().model_dump()).
            model_dump()
        )


class MultiqcJobData(MultiqcJobWithOrcabusId, Dyntastic):
    """
    The job data object
    """
    __table_name__ = environ['DYNAMODB_MULTIQC_JOB_TABLE_NAME']
    __table_host__ = environ['DYNAMODB_HOST']
    __hash_key__ = "id"

    @classmethod
    def from_dict(cls, **data) -> Self:
        """
        Alternative deserialization path to return objects by camel case
        :param data:
        :return:
        """
        # Convert keys to snake case
        data = {to_snake(k): v for k, v in data.items()}

        return cls(**data)

    # To Dictionary
    def to_dict(self, include_s3_details=False) -> 'MultiqcJobResponseDict':
        """
        Alternative serialization path to return objects by camel case
        :return:
        """
        # Update the s3 details cache if needed
        if include_s3_details:
            # Get the s3 objects
            s3_objs = get_s3_objs_from_ingest_ids_map(
                list(filter(
                    lambda ingest_id_iter_: not check_in_cache(ingest_id_iter_),
                    list(map(
                        lambda object_iter_: object_iter_.ingest_id,
                        list(filter(
                            lambda object_iter_: object_iter_ is not None,
                            [self.multiqc_html, self.multiqc_parquet]
                        ))
                    ))
                ))
            )

            for s3_obj_iter_ in s3_objs:
                update_cache(s3_obj_iter_['ingestId'], s3_obj_iter_['fileObject'])

        # Complete recursive serialization manually
        data = self.model_dump()

        # Convert keys to camel case
        # Manually serialize the sub fields
        for field_name in [
            "multiqc_html",
            "multiqc_parquet",
        ]:
            field = getattr(self, field_name)
            if field is not None:
                data[field_name] = field.to_dict()

        return MultiqcJobResponse(
            **data
        ).model_dump(
            include_s3_details=include_s3_details,
            by_alias=True
        )
