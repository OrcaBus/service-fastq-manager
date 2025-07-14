#!/usr/bin/env python3

"""
File Storage Object

The file storage object for the fastq manager is a key pair of ingest_id and s3_uri

However the s3_uri is only available on creation of the object and is not stored in the database
since the s3_uri may change, but the ingest_id is a unique identifier for the file storage object,
we only keep the ingest_id in the database, and if we need the s3 uri we query it from the file manager
"""

# Standard imports
import typing
from typing import Optional, Self, Union, TypedDict, NotRequired
from fastapi.encoders import jsonable_encoder
from pydantic import Field, BaseModel, model_validator, ConfigDict, computed_field

# Util imports
from orcabus_api_tools.filemanager import get_ingest_id_from_s3_uri
from orcabus_api_tools.filemanager.models import StorageClassType
from ..cache import get_from_cache
from ..utils import (
    to_snake, to_camel
)


class FileStorageObjectBase(BaseModel):
    ingest_id: str = Field(default="")


class FileStorageObjectResponseBase(FileStorageObjectBase):
    model_config = ConfigDict(
        alias_generator=to_camel
    )

    @model_validator(mode='before')
    def convert_keys_to_camel(cls, values):
        return {to_camel(k): v for k, v in values.items()}

    def model_dump(self, **kwargs) -> Self:
        if 'exclude_none' not in kwargs:
            kwargs['exclude_none'] = True
        # Don't include None values in the dump - i.e don't include sha256 if it is none
        return jsonable_encoder(super().model_dump(**kwargs))


# Combine the options but we need to make sure that classes know how to 'dump'
class FileStorageObjectResponseWithNoS3DetailsDict(TypedDict):
    ingestId: str


class FileStorageObjectResponseWithS3DetailsDict(TypedDict):
    ingestId: str
    s3Uri: NotRequired[str]
    storageClass: NotRequired[StorageClassType]
    sha256: NotRequired[str]


FileStorageObjectResponseDict = Union[FileStorageObjectResponseWithNoS3DetailsDict, FileStorageObjectResponseWithS3DetailsDict]

class FileStorageObjectResponseWithNoS3Details(FileStorageObjectResponseBase):
    if typing.TYPE_CHECKING:
        def model_dump(self, **kwargs) -> 'FileStorageObjectResponseWithNoS3DetailsDict':
            pass

class FileStorageObjectResponseWithS3Details(FileStorageObjectResponseBase):
    @computed_field
    def s3_uri(self) -> Optional[str]:
        # If the s3 uri is not in the cache, return None
        file_object = get_from_cache(self.ingest_id)

        if file_object is not None:
            return f"s3://{file_object['bucket']}/{file_object['key']}"

    @computed_field
    def storage_class(self) -> Optional[StorageClassType]:
        # If the s3 uri is not in the cache, return None
        file_object = get_from_cache(self.ingest_id)
        if file_object is not None:
            if file_object.get('storageClass', None) is not None:
                return file_object['storageClass']

    @computed_field
    def sha256(self) -> Optional[str]:
        # If the s3 uri is not in the cache, return None
        file_object = get_from_cache(self.ingest_id)
        if file_object is not None:
            if file_object.get('sha256', None) is not None:
                return file_object['sha256']

    if typing.TYPE_CHECKING:
        def model_dump(self, **kwargs) -> 'FileStorageObjectResponseWithS3DetailsDict':
            pass


class FileStorageObjectResponse(FileStorageObjectResponseBase):
    def model_dump(self, **kwargs) -> FileStorageObjectResponseDict:
        include_s3_details = False
        if 'include_s3_details' in kwargs:
            kwargs = kwargs.copy()
            include_s3_details = kwargs.pop('include_s3_details')

        if include_s3_details:
            return FileStorageObjectResponseWithS3Details(**dict(super().model_dump(**kwargs))).model_dump(by_alias=True)
        return FileStorageObjectResponseWithNoS3Details(**dict(super().model_dump(**kwargs))).model_dump(by_alias=True)


class FileStorageObjectCreate(FileStorageObjectBase):
    model_config = ConfigDict(
        alias_generator=to_camel
    )

    # The s3 uri of the file storage object is only available on creation
    s3_uri: Optional[str] = None

    @model_validator(mode='before')
    def convert_keys_to_camel(cls, values):
        return {to_camel(k): v for k, v in values.items()}

    @model_validator(mode='after')
    def set_ingest_id(self) -> Self:
        # Set the s3 ingest id if not provided to be from the s3 uri
        if not self.ingest_id:
            self.ingest_id = get_ingest_id_from_s3_uri(self.s3_uri)
        return self

    def model_dump(self, **kwargs) -> 'FileStorageObjectResponseDict':
        return (
            FileStorageObjectResponse(**super().model_dump(**kwargs)).
            model_dump(by_alias=True)
        )


class FileStorageObjectData(FileStorageObjectBase):
    # Convert keys to snake case prior to validation
    @model_validator(mode='before')
    def convert_keys_to_snake_case(cls, values):
        return {to_snake(k): v for k, v in values.items()}

    def to_dict(self, **kwargs) -> 'FileStorageObjectResponseDict':
        """
        Alternative Serialization method to_dict which uses the Response object
        which allows us to use the camel case keys
        :return:
        """
        return (
            FileStorageObjectResponse(**self.model_dump(**kwargs)).
            model_dump(by_alias=True)
        )
