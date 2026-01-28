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


class SomalierUriBase(BaseModel):
    somalier: FileStorageObjectData


class SomalierUriResponse(SomalierUriBase):
    somalier: FileStorageObjectResponse

    if TYPE_CHECKING:
        def model_dump(self, **kwargs) -> Self:
            pass


class SomalierUriCreate(SomalierUriBase):
    somalier: FileStorageObjectCreate

    def model_dump(self, **kwargs) -> 'SomalierUriResponse':
        return (
            SomalierUriResponse(**super().model_dump())
            .model_dump()
        )


class SomalierUriUpdate(SomalierUriCreate):
    @model_validator(mode='before')
    def load_json_string(cls, values):
        if isinstance(values, bytes):
            values = json.loads(values.decode('utf-8'))
        return values


class SomalierUriData(SomalierUriBase):
    def to_dict(self) -> 'SomalierUriResponse':
        # Complete recursive serialization manually
        data = self.model_dump()
        data['somalier'] = self.somalier.to_dict()
        return SomalierUriResponse(**data).model_dump(by_alias=True)
