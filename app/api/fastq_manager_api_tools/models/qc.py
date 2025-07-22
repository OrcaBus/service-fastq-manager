#!/usr/bin/env python3

# Standard imports
from typing import TypedDict, Optional
import logging
from decimal import Decimal
from pydantic import Field, BaseModel, model_validator, ConfigDict, ValidationError

# Local imports
from .sequali import SequaliResponse, SequaliData, SequaliCreate, SequaliResponseDict
from ..utils import to_camel, to_snake
from . import FloatDecimal

# Set basic logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QcInformationBase(BaseModel):
    insert_size_estimate: FloatDecimal = Field(default=Decimal(0))
    raw_wgs_coverage_estimate: FloatDecimal = Field(default=Decimal(0))
    r1_q20_fraction: FloatDecimal = Field(default=Decimal(0))
    r2_q20_fraction: FloatDecimal = Field(default=Decimal(0))
    r1_gc_fraction: FloatDecimal = Field(default=Decimal(0))
    r2_gc_fraction: FloatDecimal = Field(default=Decimal(0))
    duplication_fraction_estimate: FloatDecimal = Field(default=Decimal(0))
    sequali_reports: Optional[SequaliData] = None


class QcInformationResponseDict(TypedDict):
    insertSizeEstimate: Optional[float]
    rawWgsCoverageEstimate: Optional[float]
    r1Q20Fraction: Optional[float]
    r2Q20Fraction: Optional[float]
    r1GcFraction: Optional[float]
    r2GcFraction: Optional[float]
    duplicationFractionEstimate: Optional[float]
    sequaliReports: Optional[SequaliResponseDict]


class QcInformationResponse(QcInformationBase):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    sequali_reports: Optional[SequaliResponse]

    @model_validator(mode='before')
    def to_camel_case(cls, values):
        return {to_camel(key): value for key, value in values.items()}

    def model_dump(self, **kwargs) -> QcInformationResponseDict:
        # Handle specific kwargs
        include_s3_details = False
        if 'include_s3_details' in kwargs:
            kwargs = kwargs.copy()
            include_s3_details = kwargs.pop('include_s3_details')

        # Complete recursive serialization manually
        data = super().model_dump(**kwargs)

        if 'by_alias' not in kwargs:
            kwargs['by_alias'] = True

        # Serialize r1 and r2
        if self.sequali_reports:
            data['sequaliReports'] = self.sequali_reports.model_dump(**kwargs, include_s3_details=include_s3_details)
        return data


class QcInformationCreate(QcInformationBase):
    model_config = ConfigDict(
        alias_generator=to_camel
    )

    sequali_reports: Optional[SequaliCreate]

    @model_validator(mode='before')
    def to_camel_case(cls, values):
        return {to_camel(key): value for key, value in values.items()}

    def model_dump(self, **kwargs) -> 'QcInformationResponseDict':
        try:
            return (
                QcInformationResponse(**dict(super().model_dump(**kwargs))).
                model_dump(by_alias=True)
            )
        except ValidationError:
            logger.error(self)
            logger.error(kwargs)
            logger.error(super().model_dump(**kwargs))
            raise ValidationError(
                f"Failed to serialize QcInformationCreate with values: {self.model_dump()}"
            )


class QcInformationPatch(BaseModel):
    qc_obj: QcInformationCreate

    def model_dump(self, **kwargs) -> 'QcInformationResponseDict':
        return (
            QcInformationResponse(**dict(self.qc_obj.model_dump(**kwargs))).
            model_dump(**kwargs)
        )


class QcInformationData(QcInformationBase):
    # Convert keys to snake case prior to validation
    @model_validator(mode='before')
    def convert_keys_to_snake_case(cls, values):
        return {to_snake(k): v for k, v in values.items()}

    def to_dict(self) -> 'QcInformationResponseDict':
        """
        Alternative Serialization method to_dict which uses the Response object
        which allows us to use the camel case keys
        :return:
        """
        data = self.model_dump()

        if self.sequali_reports is not None:
            data['sequaliReports'] = self.sequali_reports.to_dict()

        return (
            QcInformationResponse(**data).
            model_dump(by_alias=True)
        )
