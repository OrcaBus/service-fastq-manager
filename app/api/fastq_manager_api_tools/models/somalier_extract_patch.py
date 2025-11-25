import typing
from typing import Optional

from pydantic import BaseModel

from . import ReferenceGenome
from .file_storage import FileStorageObjectCreate


class ExtractFingerprintPatch(BaseModel):
    bam_obj: Optional[FileStorageObjectCreate] = None
    reference_name: Optional[ReferenceGenome] = None
