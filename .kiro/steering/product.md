# Fastq Manager

The Fastq Manager is a microservice within the OrcaBus platform that serves as a database and RESTful API for managing FASTQ genomic sequencing files. It operates at the intersection of the filemanager and metadata manager for primary sequencing data.

## Core Responsibilities

- Track FASTQ file metadata linked to libraries, using filemanager ingest IDs (not raw S3 URIs)
- Manage read sets (R1 required, R2 optional) supporting gzip and ORA compression formats
- Orchestrate QC jobs: file size estimation, raw md5sum, NTSM fingerprinting, read count, base count estimation, sequali stats, somalier extraction
- Publish `FastqStateChange` and `FastqSetStateChange` events to EventBridge when data is updated
- Provide RESTful API endpoints for querying, creating, updating, and deleting fastq records

## Key Concepts

- **RGID**: Unique read group identifier, typically `<index>.<lane>.<instrument_run_id>` for Illumina reads
- **ULIDs**: Used for primary keys with context prefixes — `fqr.` for fastq objects, `fqs.` for fastq set objects
- **Ingest ID**: Reference to the filemanager's record, allowing the fastq manager to track files regardless of archival/movement
- **Fastq Set**: A group of fastq records belonging to the same library

## Related Services

- Upstream: File Manager, Metadata Manager
- Co-dependent: Fastq Unarchiving, Fastq Sync, Fastq Decompression, Fastq Glue
- Downstream customers: Data Sharing, Dragen WGTS DNA Pipeline, Dragen TSO500 ctDNA Pipeline

## Environments

Deployed across three environments via CodePipeline: beta → gamma → prod.
Production API: `https://fastq.prod.umccr.org/api/v1`
