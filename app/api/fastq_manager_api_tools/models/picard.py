#!/usr/bin/env python3

# Standard imports
from typing import TypedDict
import logging
from pydantic import BaseModel, ConfigDict, model_validator

# Local imports
from .file_storage import (
    FileStorageObjectData,
    FileStorageObjectResponse,
    FileStorageObjectCreate, FileStorageObjectResponseDict
)
from ..utils import to_camel

# Set basic logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PicardResponseDict(TypedDict):
    collectInsertSizeParquet: FileStorageObjectResponseDict
    collectInsertSizePdf: FileStorageObjectResponseDict
    multiqcHtml: FileStorageObjectResponseDict
    multiqcParquet: FileStorageObjectResponseDict


class PicardBase(BaseModel):
    collect_insert_size_parquet: FileStorageObjectData
    collect_insert_size_pdf: FileStorageObjectData
    multiqc_html: FileStorageObjectData
    multiqc_parquet: FileStorageObjectData


class PicardResponse(PicardBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
    )

    collect_insert_size_parquet: FileStorageObjectResponse
    collect_insert_size_pdf: FileStorageObjectResponse
    multiqc_html: FileStorageObjectResponse
    multiqc_parquet: FileStorageObjectResponse

    # Set keys to camel case
    @model_validator(mode='before')
    def convert_keys_to_camel(cls, values):
        return {to_camel(k): v for k, v in values.items()}

    def model_dump(self, **kwargs) -> PicardResponseDict:
        # Handle specific kwargs
        include_s3_details = False
        if 'include_s3_details' in kwargs:
            kwargs = kwargs.copy()
            include_s3_details = kwargs.pop('include_s3_details')

        # Complete recursive serialization manually
        data = super().model_dump(**kwargs)

        if 'by_alias' not in kwargs:
            kwargs['by_alias'] = True

        # Convert keys to camel case
        # Manually serialize the sub fields
        for field_name in [
            "collect_insert_size_parquet",
            "collect_insert_size_pdf",
            "multiqc_html",
            "multiqc_parquet",
        ]:
            field = getattr(self, field_name)
            data[to_camel(field_name)] = field.model_dump(
                **kwargs, include_s3_details=include_s3_details
            )

        return data


class PicardCreate(PicardBase):
    model_config = ConfigDict(
        alias_generator=to_camel
    )

    collect_insert_size_parquet: FileStorageObjectCreate
    collect_insert_size_pdf: FileStorageObjectCreate
    multiqc_html: FileStorageObjectCreate
    multiqc_parquet: FileStorageObjectCreate

    def model_dump(self, **kwargs) -> 'PicardResponseDict':
        return (
            PicardResponse(**super().model_dump()).
            model_dump()
        )


class PicardData(PicardBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    def to_dict(self) -> 'PicardResponseDict':
        """
        Alternative Serialization method to_dict which uses the Response object
        which allows us to use the camel case keys
        :return:
        """
        # Complete recursive serialization manually
        data = self.model_dump()

        # Convert keys to camel case
        # Manually serialize the sub fields
        for field_name in [
            "collect_insert_size_parquet",
            "collect_insert_size_pdf",
            "multiqc_html",
            "multiqc_parquet",
        ]:
            field = getattr(self, field_name)
            data[field_name] = field.to_dict()

        return (
            PicardResponse(**data).
            model_dump(by_alias=True)
        )
