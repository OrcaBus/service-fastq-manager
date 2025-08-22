Fastq Manager
================================================================================

- [Fastq Manager](#fastq-manager)
  - [Service Description](#service-description)
    - [Related Services](#related-services)
      - [Upstream Services](#upstream-services)
      - [Co-dependent services](#co-dependent-services)
      - [Fastq Manager Customers](#fastq-manager-customers)
    - [API Endpoints](#api-endpoints)
    - [Published Events](#published-events)
    - [Release management](#release-management)
  - [Operation](#operation)
    - [SOPs](#sops)
    - [Usage Examples](#usage-examples)
  - [Infrastructure \& Deployment :construction:](#infrastructure--deployment-construction)
    - [Stateful](#stateful)
    - [Stateless](#stateless)
    - [CDK Commands](#cdk-commands)
    - [Stacks](#stacks)
  - [Development](#development)
    - [Project Structure](#project-structure)
    - [Setup](#setup)
      - [Requirements](#requirements)
      - [Install Dependencies](#install-dependencies)
    - [Conventions](#conventions)
    - [Linting \& Formatting](#linting--formatting)
    - [Testing](#testing)
  - [Glossary \& References](#glossary--references)


Service Description
--------------------------------------------------------------------------------

The Fastq Manager serves as both a database and a RESTful API endpoint for performing
statistics on the Fastq files in the database. This service performs as an intersection
between the filemanager and the metadata manager for primary data.

Each fastq must be linked to a library, but can be searched for via other metadata parameters
through the REST API.

Each fastq will have an associated read set. The read set must comprise an R1 file while the R2 file is optional.

The Fastq manager does NOT store the S3 URI but instead stores the filemanager's ingest ID,
this means that if the file is archived, the fastq manager will still access the correct file since the moved
file will still have the same ingest ID. Read set attributes such as s3Uri or storage class are only calculated
when the REST API is called.

The Fastq Manager can store both gzip compressed and ORA compressed fastq files.

Each fastq in the database must have a unique RGID. The RGID for Illumina reads is typically,
`<index>.<lane>.<instrument_run_id>`.

The fastq manager uses [ulids](https://github.com/ulid/spec) for its primary keys along with a context prefix.

For fastq objects, the prefix is `fqr.` and for fastq set objects, the prefix is `fqs.`.

**JOBS**

The fastq manager can run jobs on itself, such as:
* Estimating the gzip file size for an ORA compressed fastq file
  * (required to stream from the decompressor back to s3 for fastq gzipped files estimated to be over 50 Gb).
* Calculating the raw md5sum for a ORA file.
* Calculating the [NTSM fingerprint](https://github.com/JustinChu/ntsm) for a fastq pair.
* Calcuating the number of reads in a fastq file.
* Estimating the number of non-N bases in a fastq file.

Whenever a fastq file is updated, the fastq manager pushes the FastqStateChange event to the event bus.

### Related Services

#### Upstream Services

- [File Manager](https://github.com/OrcaBus/service-filemanager)
- [Metadata Manager](https://github.com/OrcaBus/service-metadata-manager)

#### Co-dependent services

- [Fastq Unarchiving Service]((https://github.com/OrcaBus/service-fastq-unarchving-manager))
- [Fastq Sync Service](https://github.com/OrcaBus/service-fastq-sync-manager)
- [Fastq Decompression Service](https://github.com/OrcaBus/service-fastq-decompression-manager)

#### Fastq Manager Customers

- [Fastq Glue Service](https://github.com/OrcaBus/service-fastq-glue)
- [Data Sharing Service](https://github.com/OrcaBus/service-data-sharing-manager)
- [Dragen WGTS DNA Pipeline Service](https://github.com/OrcaBus/service-dragen-wgts-dna-pipeline-manager)
- [Dragen TSO500 ctDNA Pipeline Service](https://github.com/OrcaBus/service-dragen-tso500-ctdna-pipeline-manager)


### API Endpoints

This service provides a RESTful API following OpenAPI conventions. \
The production endpoint is available here: [https://fastq.prod.umccr.org/api/v1](https://fastq.prod.umccr.org/api/v1) \
The Swagger documentation of the production endpoint is available here: [https://fastq.prod.umccr.org/schema/swagger-ui](https://fastq.prod.umccr.org/schema/swagger-ui)

As a general rule of thumb, **fqr** ids are used for api/v1/fastq endpoints, while **fqs** ids are used for api/v1/fastqSet endpoints.

### Published Events

| Name / DetailType  | Source                 | Schema Link | Description              |
|--------------------|------------------------|-------------|--------------------------|
| `FastqStateChange` | `orcabus.fastqmanager` | # FIXME     | A Fastq has been updated |

### Release management

The service employs a fully automated CI/CD pipeline that automatically builds and releases all changes to the `main` code branch.

Operation
--------------------------------------------------------------------------------

### SOPs

- [FQM.1 - Invalidate Fastq Pair](./doc/operation/sop/FQM.1/FQM.1-InvalidateFastqPair.md)

### Usage Examples

- [Setup: Authentication](./doc/operation/Examples.md#setup-authentication)
- [Get Fastqs (api/v1/fastq)](./doc/operation/Examples.md#get-fastqs-apiv1fastq)
- [Get Fastq by RGID (api/v1/rgid/)](./doc/operation/Examples.md#get-fastq-by-rgid-apiv1rgid)
- [Get Fastq Sets (api/v1/fastqSet)](./doc/operation/Examples.md#get-fastq-sets-apiv1fastqset)
- [Run Jobs on Fastqs](./doc/operation/Examples.md#run-jobs-on-fastqs)
- [Creating Fastq Objects](./doc/operation/Examples.md#creating-fastq-objects)
- [Deleting Fastq Objects](./doc/operation/Examples.md#deleting-fastq-objects)
- [Amending Fastqs](./doc/operation/Examples.md#amending-fastqs)
- [Amending Fastq Sets](./doc/operation/Examples.md#amending-fastq-sets)
- [For Download / Streaming](./doc/operation/Examples.md#for-download--streaming)
- [Comparing Fastqs within a fastq set](./doc/operation/Examples.md#comparing-fastqs-within-a-fastq-set)
- [Comparing Two Fastq Sets](./doc/operation/Examples.md#comparing-two-fastq-sets)
- [MultiQC Summaries](./doc/operation/Examples.md#multiqc-summaries)
	- [Get all fastqs](./doc/operation/Examples.md#get-all-fastqs)
	- [Get missing QC stats](./doc/operation/Examples.md#get-missing-qc-stats)
	- [Generate MultiQC Summary](./doc/operation/Examples.md#generate-multiqc-summary)


Infrastructure & Deployment :construction:
--------------------------------------------------------------------------------

Short description with diagrams where appropriate.
Deployment settings / configuration (e.g. CodePipeline(s) / automated builds).

Infrastructure and deployment are managed via CDK. This template provides two types of CDK entry points: `cdk-stateless` and `cdk-stateful`.


### Stateful

- S3 Buckets
  - The fastq cache bucket (fastq-manager-cache-472057503814-ap-southeast-2) is used to store temp outputs from ECS tasks
  - The ntsm bucket (ntsm-fingerprints-472057503814-ap-southeast-2) is used to store NTSM fingerprints.

- DynamoDB
  - We use three tables to handle the API interface.
  - FastqDataTable
  - FastqSetDataTable
  - FastqJobsTable

### Stateless

- Lambdas
- Step Functions
- Api Gateway
- ECS


### CDK Commands

You can access CDK commands using the `pnpm` wrapper script.

- **`cdk-stateless`**: Used to deploy stacks containing stateless resources (e.g., AWS Lambda), which can be easily redeployed without side effects.
- **`cdk-stateful`**: Used to deploy stacks containing stateful resources (e.g., AWS DynamoDB, AWS RDS), where redeployment may not be ideal due to potential side effects.

The type of stack to deploy is determined by the context set in the `./bin/deploy.ts` file. This ensures the correct stack is executed based on the provided context.

For example:

```sh
# Deploy a stateless stack
pnpm cdk-stateless <command>

# Deploy a stateful stack
pnpm cdk-stateful <command>
```

### Stacks

This CDK project manages multiple stacks. The root stack (the only one that does not include `DeploymentPipeline` in its stack ID) is deployed in the toolchain account and sets up a CodePipeline for cross-environment deployments to `beta`, `gamma`, and `prod`.

**CDK Stateful**

To list all available stacks, run:

```sh
StatefulFastqStack
StatefulFastqStack/StatefulFastqStackPipeline/OrcaBusBeta/StatefulFastqStack (OrcaBusBeta-StatefulFastqStack)
StatefulFastqStack/StatefulFastqStackPipeline/OrcaBusGamma/StatefulFastqStack (OrcaBusGamma-StatefulFastqStack)
StatefulFastqStack/StatefulFastqStackPipeline/OrcaBusProd/StatefulFastqStack (OrcaBusProd-StatefulFastqStack)
```

**CDK Stateless**

To list all available stacks, run:

```sh
pnpm cdk-stateless ls
```

Output


```sh
StatelessFastqStack
StatelessFastqStack/StatelessFastqStackPipeline/OrcaBusBeta/StatelessFastqStack (OrcaBusBeta-StatelessFastqStack)
StatelessFastqStack/StatelessFastqStackPipeline/OrcaBusGamma/StatelessFastqStack (OrcaBusGamma-StatelessFastqStack)
StatelessFastqStack/StatelessFastqStackPipeline/OrcaBusProd/StatelessFastqStack (OrcaBusProd-StatelessFastqStack)
```


Development
--------------------------------------------------------------------------------

### Project Structure

The root of the project is an AWS CDK project where the main application logic lives inside the `./app` folder.

The project is organized into the following key directories:

- **`./app`**: Contains the main application logic. You can open the code editor directly in this folder, and the application should run independently.

- **`./bin/deploy.ts`**: Serves as the entry point of the application. It initializes two root stacks: `stateless` and `stateful`. You can remove one of these if your service does not require it.

- **`./infrastructure`**: Contains the infrastructure code for the project:
  - **`./infrastructure/toolchain`**: Includes stacks for the stateless and stateful resources deployed in the toolchain account. These stacks primarily set up the CodePipeline for cross-environment deployments.
  - **`./infrastructure/stage`**: Defines the stage stacks for different environments:
    - **`./infrastructure/stage/config.ts`**: Contains environment-specific configuration files (e.g., `beta`, `gamma`, `prod`).
    - **`./infrastructure/stage/stack.ts`**: The CDK stack entry point for provisioning resources required by the application in `./app`.

- **`.github/workflows/pr-tests.yml`**: Configures GitHub Actions to run tests for `make check` (linting and code style), tests defined in `./test`, and `make test` for the `./app` directory. Modify this file as needed to ensure the tests are properly configured for your environment.

- **`./test`**: Contains tests for CDK code compliance against `cdk-nag`. You should modify these test files to match the resources defined in the `./infrastructure` folder.


### Setup

#### Requirements

```sh
node --version
v22.9.0

# Update Corepack (if necessary, as per pnpm documentation)
npm install --global corepack@latest

# Enable Corepack to use pnpm
corepack enable pnpm

```

#### Install Dependencies

To install all required dependencies, run:

```sh
make install
```

### Conventions

### Linting & Formatting

Automated checks are enforces via pre-commit hooks, ensuring only checked code is committed. For details consult the `.pre-commit-config.yaml` file.

Manual, on-demand checking is also available via `make` targets (see below). For details consult the `Makefile` in the root of the project.


To run linting and formatting checks on the root project, use:

```sh
make check
```

To automatically fix issues with ESLint and Prettier, run:

```sh
make fix
```

### Testing


Unit tests are available for most of the business logic. Test code is hosted alongside business in `/tests/` directories.

```sh
make test
```

Glossary & References
--------------------------------------------------------------------------------

For general terms and expressions used across OrcaBus services, please see the platform [documentation](https://github.com/OrcaBus/wiki/blob/main/orcabus-platform/README.md#glossary--references).

Service specific terms:

| Term      | Description                                      |
|-----------|--------------------------------------------------|
| Foo | ... |
| Bar | ... |
