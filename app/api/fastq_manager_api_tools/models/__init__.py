import json
from typing import (
    TypedDict, Optional, Annotated,
    Literal,
    NotRequired
)
from decimal import Decimal

from pydantic import PlainValidator, PlainSerializer

# Miscellanous Enums
CompressionFormatType = Literal[
    'ORA',
    'GZIP',
]

BoolQueryOptions = Literal[
    'ALL',
    True,
    False
]

BoolQueryOptionsJsonType = Literal [
    'ALL',
    'true',
    'false'
]

BoolQueryOptionsAnnotated = Annotated[
    BoolQueryOptions,
    PlainValidator(
        lambda x: json.loads(x) if x in ['true', 'false'] else x,
        json_schema_input_type=BoolQueryOptionsJsonType
    )
]


class FastqListRowDict(TypedDict):
    # Typed Dicts are minimal versions of pydantic BaseModels
    # Don't need to work on snake case vs camel case conversions
    # As CWLDict is merely used to type hint a controlled output
    rgid: str
    rglb: str
    rgsm: str
    lane: int

    # Optional fields
    rgcn: NotRequired[str] # Centre name
    rgds: NotRequired[str] # Description
    rgdt: NotRequired[str] # Date
    rgpl: NotRequired[str] # Platform

    # File Uris
    read1FileUri: str
    read2FileUri: NotRequired[str]


class PresignedUrl(TypedDict):
    s3Uri: str
    presignedUrl: str
    expiresAt: str


class PresignedUrlModel(TypedDict):
    r1: PresignedUrl
    r2: Optional[PresignedUrl]


FloatDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda x: float(x), return_type=float, when_used='json')
]


PlatformType = Literal[
    'Illumina'
]

CenterType = Literal[
    'UMCCR',  # Default
    'AGRF'
]


class EmptyDict(TypedDict):
    pass

JobStatusType = Literal[
    'PENDING',
    'RUNNING',
    'FAILED',
    'SUCCEEDED',
]
