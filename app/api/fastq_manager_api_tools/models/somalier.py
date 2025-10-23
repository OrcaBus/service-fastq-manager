#!/usr/bin/env python3

# Standard imports
from pydantic import BaseModel, model_validator
from typing import Self
import logging
import json
from typing import TYPE_CHECKING

# Local imports
from .file_storage import (
    FileStorageObjectResponse,
    FileStorageObjectData,
    FileStorageObjectCreate
)

# Set basic logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class somalierUriBase(BaseModel):
    somalier: FileStorageObjectData


class somalierUriResponse(somalierUriBase):
    somalier: FileStorageObjectResponse

    if TYPE_CHECKING:
        def model_dump(self, **kwargs) -> Self:
            pass


class somalierUriCreate(somalierUriBase):
    somalier: FileStorageObjectCreate

    def model_dump(self, **kwargs) -> 'somalierUriResponse':
        return (
            somalierUriResponse(**super().model_dump()).
            model_dump()
        )


class somalierUriUpdate(somalierUriCreate):
    @model_validator(mode='before')
    def load_json_string(cls, values):
        if isinstance(values, bytes):
            values = json.loads(values.decode('utf-8'))
        return values


class somalierUriData(somalierUriBase):
    def to_dict(self) -> 'somalierUriResponse':
        # Complete recursive serialization manually
        data = self.model_dump()
        data['somalier'] = self.somalier.to_dict()
        return somalierUriResponse(**data).model_dump(by_alias=True)
