#!/usr/bin/env python3

"""
FastqSet Job model, used for fastq set job management
"""

# Standard imports
import typing
from os import environ
from typing import Optional, Self, ClassVar, List

from dyntastic import Dyntastic
from pydantic import Field, BaseModel, model_validator, ConfigDict
from datetime import datetime, timezone, timedelta
from fastapi_tools import QueryPaginatedResponse

# Util imports
from . import FastqSetJobStatusType, FastqSetJobType
from ..utils import (
    to_camel, get_ulid, get_fastq_set_endpoint_url
)
from ..globals import FSJ_PREFIX, DYNAMODB_FASTQ_SET_JOB_TABLE_NAME_ENV_VAR


def default_start_time_factory() -> datetime:
    """
    Default factory for the start time of the job
    :return: The current datetime
    """
    return datetime.now(timezone.utc)


def default_ttl_factory() -> int:
    """
    Default factory for the TTL of the job
    :return: The current datetime in ISO format
    """
    return int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp())


class FastqSetJobBase(BaseModel):
    fastq_set_id: str
    job_type: FastqSetJobType


class FastqSetJobOrcabusId(BaseModel):
    # fsj.ABCDEFGHIJKLMNOP
    id: str = Field(default_factory=lambda: f"{FSJ_PREFIX}.{get_ulid()}")


class FastqSetJobWithId(FastqSetJobBase, FastqSetJobOrcabusId):
    """
    Order class inheritance this way to ensure that the id field is set first
    """
    # We also have the steps execution id as an attribute to add
    steps_execution_arn: Optional[str] = None
    status: FastqSetJobStatusType = Field(default='PENDING')
    start_time: datetime = Field(default_factory=default_start_time_factory)
    ttl: int = Field(default_factory=default_ttl_factory)
    end_time: Optional[datetime] = None


class FastqSetJobResponse(FastqSetJobWithId):
    model_config = ConfigDict(
        alias_generator=to_camel
    )

    # Set keys to camel case
    @model_validator(mode='before')
    def convert_keys_to_camel(cls, values):
        return {to_camel(k): v for k, v in values.items()}

    # Set the model_dump method response
    if typing.TYPE_CHECKING:
        def model_dump(self, **kwargs) -> Self:
            pass


class FastqSetJobCreate(FastqSetJobBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    def model_dump(self, **kwargs) -> 'FastqSetJobResponse':
        return (
            FastqSetJobResponse(**super().model_dump()).
            model_dump()
        )


class FastqSetJobData(FastqSetJobWithId, Dyntastic):
    """
    The fastq set job data object
    """
    __table_name__ = environ[DYNAMODB_FASTQ_SET_JOB_TABLE_NAME_ENV_VAR]
    __table_host__ = environ['DYNAMODB_HOST']
    __hash_key__ = "id"

    # To Dictionary
    def to_dict(self) -> 'FastqSetJobResponse':
        """
        Alternative serialization path to return objects by camel case
        :return:
        """
        return FastqSetJobResponse(
            **dict(self.model_dump())
        ).model_dump(by_alias=True)


class FastqSetJobQueryPaginatedResponse(QueryPaginatedResponse):
    """
    FastqSet Job Query Response, includes a list of jobs, the total
    """
    url_placeholder: ClassVar[str] = get_fastq_set_endpoint_url() + "/{fastq_set_id}/jobs"
    results: List[FastqSetJobResponse]

    @classmethod
    def resolve_url_placeholder(cls, **kwargs) -> str:
        # Get fastq set id from the kwargs
        fastq_set_id = kwargs.get("fastq_set_id")

        # Get the url placeholder
        return cls.url_placeholder.format(fastq_set_id=fastq_set_id)
