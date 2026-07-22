# Product Overview

The Fastq Manager is a service in the OrcaBus platform that serves as a database and RESTful API for managing FASTQ file metadata. It sits at the intersection of the File Manager and Metadata Manager services.

## Core Concepts

- **Fastq (fqr)**: A single FASTQ file record, linked to a library. Identified by a ULID with prefix `fqr.`
- **Fastq Set (fqs)**: A grouping of FASTQ records. Identified by a ULID with prefix `fqs.`
- **Read Set**: A pair of FASTQ files (R1 required, R2 optional)
- **RGID**: Read Group ID, typically `<index>.<lane>.<instrument_run_id>` for Illumina reads
- **Jobs**: Background tasks (base count estimation, md5sum calculation, NTSM fingerprinting, read counting, sequali QC stats)

## Key Design Decisions

- Stores filemanager ingest IDs, NOT S3 URIs directly. This decouples storage location from identity.
- Supports both gzip and ORA compressed FASTQ files.
- Uses ULIDs with context prefixes for primary keys.
- Publishes `FastqStateChange` and `FastqSetStateChange` events to EventBridge on updates.

## Related Services

- **Upstream**: File Manager, Metadata Manager
- **Co-dependent**: Fastq Unarchiving, Fastq Sync, Fastq Decompression, Fastq Glue
- **Downstream consumers**: Data Sharing, Dragen WGTS DNA Pipeline, Dragen TSO500 ctDNA Pipeline

## API

- Production endpoint: `https://fastq.prod.umccr.org/api/v1`
- Swagger docs: `https://fastq.prod.umccr.org/schema/swagger-ui`
- `fqr` IDs → `/api/v1/fastq` endpoints
- `fqs` IDs → `/api/v1/fastqSet` endpoints
