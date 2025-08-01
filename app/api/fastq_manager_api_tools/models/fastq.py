#!/usr/bin/env python3
from functools import reduce
from operator import concat

# Standard imports
from dyntastic import Dyntastic
from os import environ

from fastapi.encoders import jsonable_encoder
from pydantic import Field, BaseModel, model_validator, ConfigDict, computed_field
from typing import Optional, List, ClassVar, TypedDict
from fastapi_tools import QueryPaginatedResponse

# Layer imports
from orcabus_api_tools.filemanager import (
    get_s3_uri_from_ingest_id, get_presigned_url_from_ingest_id,
    get_presigned_url_expiry,
    get_s3_objs_from_ingest_ids_map
)
from orcabus_api_tools.metadata import get_library_from_library_orcabus_id

# Local imports
from datetime import datetime
from . import FastqListRowDict, PresignedUrlModel, CenterType, PlatformType
from ..cache import update_cache, check_in_cache
from ..globals import FQR_CONTEXT_PREFIX, EVENT_BUS_NAME_ENV_VAR
from ..utils import (
    get_ulid,
    datetime_to_isoformat,
    to_snake, to_camel, datetime_to_hf_format, get_fastq_endpoint_url, datetime_to_isodate
)

from .fastq_pair import (
    FastqPairStorageObjectData, FastqPairStorageObjectResponse,
    FastqPairStorageObjectCreate, FastqPairStorageObjectResponseDict
)
from .file_storage import (
    FileStorageObjectData, FileStorageObjectResponse,
    FileStorageObjectCreate, FileStorageObjectResponseDict
)

from .library import LibraryData, LibraryResponse, LibraryResponseDict
from .qc import QcInformationData, QcInformationResponse, QcInformationCreate, QcInformationResponseDict


class FastqBase(BaseModel):
    # FastqListRow base attributes
    # Missing the following, id, rgid_ext and library_orcabus_id
    # We add in the 'id' in the FastqListRowResponse model
    # We add in the 'id', 'rgid_ext' and 'library_orcabus_id' in the FastqListRow model
    # However the CreateFastqListRow model does not require these fields to be set
    # So we start with the greatest common denominator and extend classes from there
    index: str = None
    lane: int = Field(default=1)
    instrument_run_id: str

    # The library object that this fastq list row is associated with
    library: LibraryData

    # Add in other rg components
    platform: Optional[PlatformType] = None
    center: Optional[CenterType] = None

    # Add in read group date
    date: Optional[datetime] = None

    # We compute 'description' from the library object when writing to fastqListRows

    # Storage Metadata - This attaches the filemanager information to the fastq list row pairing
    # There may be duplicates since we have a copy in the cache bucket and the archive storage bucket
    read_set: Optional[FastqPairStorageObjectData] = None

    # QC Information
    qc: Optional[QcInformationData] = None

    # Additional metadata
    read_count: Optional[int] = None
    base_count_est: Optional[int] = None

    # Boolean decision-making logic
    is_valid: Optional[bool] = None  # Is the fastq pair valid

    # Future
    ntsm: Optional[FileStorageObjectData] = None


class FastqOrcabusId(BaseModel):
    # fqr.ABCDEFGHIJKLMNOP
    # BCLConvert Metadata attributes
    id: str = Field(default_factory=lambda: f"{FQR_CONTEXT_PREFIX}.{get_ulid()}")

    fastq_set_id: Optional[str] = None


class FastqWithId(FastqBase, FastqOrcabusId):
    """
    Order class inheritance this way to ensure that the id field is set first
    """
    pass


class FastqResponseDict(TypedDict):
    id: str
    fastqSetId: Optional[str]
    index: str
    lane: int
    instrumentRunId: str
    library: LibraryResponseDict
    platform: Optional[PlatformType]
    center: Optional[CenterType]
    date: Optional[datetime]
    readSet: Optional[FastqPairStorageObjectResponseDict]
    qc: Optional[QcInformationResponseDict]
    ntsm: Optional[FileStorageObjectResponseDict]
    readCount: Optional[int]
    baseCountEst: Optional[int]
    isValid: Optional[bool]


class FastqResponse(FastqWithId):
    # Identical to the CreateFastqListRow model but with the addition of the id field
    # Set the model configuration
    model_config = ConfigDict(
        alias_generator=to_camel
    )

    # Manually configure the sub fields with their own model configurations
    library: LibraryResponse

    read_set: Optional[FastqPairStorageObjectResponse] = None

    qc: Optional[QcInformationResponse] = None

    ntsm: Optional[FileStorageObjectResponse] = None

    # Set keys to camel case
    @model_validator(mode='before')
    def convert_keys_to_camel(cls, values):
        return {to_camel(k): v for k, v in values.items()}

    # Set the model_dump method response
    def model_dump(self, **kwargs) -> FastqResponseDict:
        # Handle specific kwargs
        include_s3_details = False
        if 'include_s3_details' in kwargs:
            kwargs = kwargs.copy()
            include_s3_details = kwargs.pop('include_s3_details')

        # Recursively serialize the object
        data = super().model_dump(**kwargs)

        # Convert 'date' to hf field (we dont need the timestamp bit)
        if data.get('date') is not None:
            data['date'] = datetime_to_isodate(data['date'])

        # Manually serialize the sub fields
        for field_name in ["library", "read_set", "qc", "ntsm"]:
            field = getattr(self, field_name)
            if field is None:
                continue
            if field_name in ['read_set', 'ntsm', 'qc']:
                data[to_camel(field_name)] = field.model_dump(
                    **kwargs, include_s3_details=include_s3_details
                )
            else:
                data[to_camel(field_name)] = field.model_dump(**kwargs)

        return jsonable_encoder(data)


class FastqCreate(FastqBase):
    # Set the model configuration
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    # Manually configure the sub fields with their own model configurations
    library: LibraryResponse

    read_set: Optional[FastqPairStorageObjectCreate] = None

    qc: Optional[QcInformationCreate] = None

    ntsm: Optional[FileStorageObjectCreate] = None

    def model_dump(self, **kwargs) -> 'FastqResponseDict':
        return (
            FastqResponse(**super().model_dump(**kwargs)).
            model_dump(**kwargs)
        )


class FastqData(FastqWithId, Dyntastic):
    # We don't use aliases, instead we convert all keys to snake case first
    # And then we convert them back to camel case in the to_dict method.
    # This separates out serialization to the database store and serialization to the client
    __table_name__ = environ['DYNAMODB_FASTQ_TABLE_NAME']
    __table_host__ = environ['DYNAMODB_HOST']
    __hash_key__ = "id"

    @model_validator(mode='before')
    def convert_keys_to_snake_case(cls, values):
        return {to_snake(k): v for k, v in values.items()}

    @computed_field
    def rgid_ext(self) -> str:
        return ".".join(map(
            str,
            list(filter(
                lambda x: x is not None,
                # As new platforms are added, this may need to be updated
                [self.index, self.lane, self.instrument_run_id]
            ))
        ))

    @computed_field
    def library_orcabus_id(self) -> str:
        return self.library.orcabus_id

    def to_dict(self, include_s3_details: Optional[bool] = False) -> 'FastqResponseDict':
        """
        Alternative serialization path to return objects by camel case
        :return:
        """
        if include_s3_details and self.read_set is not None and not environ.get(EVENT_BUS_NAME_ENV_VAR) == 'local':
            # Get the s3 objects
            s3_objs = get_s3_objs_from_ingest_ids_map(
                list(filter(
                    lambda ingest_id_iter_: not check_in_cache(ingest_id_iter_),
                    list(map(
                        lambda read_set_obj_iter_: read_set_obj_iter_.ingest_id,
                        list(filter(
                            lambda read_set_obj_iter_: read_set_obj_iter_ is not None,
                            [self.read_set.r1, self.read_set.r2]
                        ))
                    ))
                ))
            )

            # Check if the ntsm object is present
            if self.ntsm and self.ntsm.ingest_id is not None:
                s3_objs.extend(
                    get_s3_objs_from_ingest_ids_map(
                        list(filter(
                            lambda ingest_id_iter_: not check_in_cache(ingest_id_iter_),
                            [self.ntsm.ingest_id]
                        ))
                    )
                )

            # Check if the qc object is present and has sequali reports
            if self.qc is not None and self.qc.sequali_reports is not None:
                s3_objs.extend(
                    get_s3_objs_from_ingest_ids_map(
                        list(filter(
                            lambda ingest_id_iter_: not check_in_cache(ingest_id_iter_),
                            [
                                self.qc.sequali_reports.sequali_html.ingest_id,
                                self.qc.sequali_reports.sequali_parquet.ingest_id,
                                self.qc.sequali_reports.multiqc_html.ingest_id,
                                self.qc.sequali_reports.multiqc_parquet.ingest_id,
                            ]
                        ))
                    )
                )

            for s3_obj_iter_ in s3_objs:
                update_cache(s3_obj_iter_['ingestId'], s3_obj_iter_['fileObject'])

        return FastqResponse(
            **self.model_dump(
                exclude={"rgid_ext", "library_orcabus_id"},
            )
        ).model_dump(
            include_s3_details=include_s3_details, by_alias=True
        )

    def to_fastq_list_row(self) -> FastqListRowDict:
        """
        Return as a CWL input object
        :return:
        """
        library_obj = get_library_from_library_orcabus_id(str(self.library_orcabus_id))

        library_description_list = [
            f"Library ID: {library_obj['libraryId']}",
            f"Sequenced on {datetime_to_hf_format(self.date)} at {self.center}"
            if self.date is not None and self.center is not None
            else "",
            f"Phenotype: {library_obj['phenotype']}" if library_obj['phenotype'] else None,
            f"Assay: {library_obj['assay']}" if library_obj['assay'] else None,
            f"Type: {library_obj['type']}" if library_obj['type'] else None,
        ]

        library_description = " / ".join(map(
            str,
            list(filter(
                lambda library_description_iter_: library_description_iter_ is not None,
                library_description_list
            ))
        ))

        return FastqListRowDict(
            **dict(filter(
                lambda kv: kv[1] is not None,
                dict({
                    "rgid": ".".join(map(str, list(filter(
                        lambda x: x is not None,
                        # As new platforms are added, this may need to be updated
                        [self.index, self.lane, self.instrument_run_id]
                    )))),
                    "rglb": self.library.library_id,
                    "rgsm": self.library.library_id,
                    "rgcn": self.center if self.center else None,
                    "rgpl": self.platform if self.platform else None,
                    "rgdt": datetime_to_isodate(self.date) if self.date else None,
                    "rgds": library_description,
                    "lane": self.lane,
                    "read1FileUri": get_s3_uri_from_ingest_id(self.read_set.r1.ingest_id),
                    "read2FileUri": get_s3_uri_from_ingest_id(self.read_set.r2.ingest_id),
                }).items()
            ))
        )

    def presign_uris(self) -> PresignedUrlModel:
        # Get all unarchived files
        # Presign the URIs
        r1_presigned_url = get_presigned_url_from_ingest_id(self.read_set.r1.ingest_id)
        presigned_objects = {
            "r1": {
                "s3Uri": get_s3_uri_from_ingest_id(self.read_set.r1.ingest_id),
                "presignedUrl": r1_presigned_url,
                "expiresAt": datetime_to_isoformat(get_presigned_url_expiry(r1_presigned_url))
            }
        }
        if self.read_set.r2:
            r2_presigned_url = get_presigned_url_from_ingest_id(self.read_set.r2.ingest_id)
            presigned_objects["r2"] = {
                "s3Uri": get_s3_uri_from_ingest_id(self.read_set.r2.ingest_id),
                "presignedUrl": r2_presigned_url,
                "expiresAt": datetime_to_isoformat(get_presigned_url_expiry(r2_presigned_url))
            }

        return PresignedUrlModel(
            **presigned_objects
        )


class FastqListResponse(BaseModel):
    # List response
    fastq_list: List[FastqData]
    include_s3_details: Optional[bool] = False

    def model_dump(self, **kwargs) -> List[FastqResponseDict]:
        if len(self.fastq_list) == 0:
            return []

        if not self.include_s3_details:
            return list(map(lambda fastq_iter_: fastq_iter_.to_dict(), self.fastq_list))

        # Collect the s3 ingest ids for the fastq list rows
        fastqs_with_readsets = list(filter(
            lambda fastq_iter_: fastq_iter_.read_set is not None,
            self.fastq_list
        ))

        r1_ingest_ids = list(map(
            lambda fastq_iter_: fastq_iter_.read_set.r1.ingest_id,
            fastqs_with_readsets
        ))

        r2_ingest_ids = list(map(
            lambda fastq_iter_: fastq_iter_.read_set.r2.ingest_id,
            list(filter(
                lambda fastq_iter_: fastq_iter_.read_set.r2 is not None,
                fastqs_with_readsets
            ))
        ))

        ntsm_ingest_ids = list(map(
            lambda fastq_iter_: fastq_iter_.ntsm.ingest_id,
            list(filter(
                lambda fastq_iter_: fastq_iter_.ntsm is not None,
                fastqs_with_readsets
            ))
        ))

        # Get the qc ingest ids
        try:
            qc_ingest_ids = list(reduce(
                concat,
                list(map(
                    lambda fastq_iter_: [
                        fastq_iter_.qc.sequali_reports.sequali_html.ingest_id,
                        fastq_iter_.qc.sequali_reports.sequali_parquet.ingest_id,
                        fastq_iter_.qc.sequali_reports.multiqc_html.ingest_id,
                        fastq_iter_.qc.sequali_reports.multiqc_parquet.ingest_id,
                    ],
                    list(filter(
                        lambda fastq_iter_: fastq_iter_.qc is not None and fastq_iter_.qc.sequali_reports is not None,
                        fastqs_with_readsets
                    ))
                ))
            ))
        except TypeError as e:
            # TypeError: reduce() of empty iterable with no initial value
            qc_ingest_ids = []

        # Get the ntsm s3 uris
        s3_list_dict = get_s3_objs_from_ingest_ids_map(
            list(filter(
                lambda ingest_id_iter_: not check_in_cache(ingest_id_iter_),
                r1_ingest_ids + r2_ingest_ids + ntsm_ingest_ids + qc_ingest_ids
            ))
        )

        # Update the cache with the s3 uris
        for row in s3_list_dict:
            update_cache(row['ingestId'], row['fileObject'])

        # Now re-dump the fastq list rows
        return list(map(
            lambda fastq_iter_: fastq_iter_.to_dict(include_s3_details=True),
            self.fastq_list
        ))


class FastqQueryPaginatedResponse(QueryPaginatedResponse):
    url_placeholder: ClassVar[str] = get_fastq_endpoint_url()
    results: List[FastqResponseDict]

    @classmethod
    def resolve_url_placeholder(cls, **kwargs) -> str:
        # Get the url placeholder
        return cls.url_placeholder
