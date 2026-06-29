# Tech Stack

## Languages

- **TypeScript** (5.9.x): Infrastructure as Code (CDK), tests
- **Python** (3.14 runtime for Lambdas): Application logic, API, Lambda handlers

## Infrastructure (CDK)

- AWS CDK v2.260.0
- `@orcabus/platform-cdk-constructs` — shared OrcaBus CDK constructs
- `@aws-cdk/aws-lambda-python-alpha` — Python Lambda packaging with UV
- `cdk-nag` — compliance/security validation

## Application (Python)

- **FastAPI** — REST API framework
- **Mangum** — Lambda adapter for FastAPI (ASGI to Lambda handler)
- **Pydantic v2** — Data validation and serialization
- **Dyntastic** — DynamoDB ORM built on Pydantic
- **ulid-py** — ULID generation for primary keys

## Package Management

- **pnpm 11.7.0** — Node.js package manager (enforced via corepack)
- **UV** — Python package manager (used by `PythonUvFunction` CDK construct for Lambda bundling)
- Node.js 22.x required

## Testing

- **Jest 30** + ts-jest — CDK infrastructure tests and cdk-nag compliance
- **pytest** + httpx — Python API integration tests (run against local DynamoDB)

## Linting & Formatting

- **ESLint 10** + typescript-eslint — TypeScript linting
- **Prettier** — Code formatting (TypeScript, JSON, YAML)
- **pre-commit** — Git hooks for secrets detection, credential detection, branch protection

## AWS Services Used

- DynamoDB (4 tables)
- S3 (cache, NTSM fingerprints, sequali outputs, reference data)
- API Gateway with Cognito authentication
- Lambda (18 functions — Python UV and Docker-based)
- ECS Fargate (8 tasks — Alpine Docker containers)
- Step Functions (9 state machines for QC workflows)
- EventBridge (OrcaBusMain bus)
- CodePipeline (CI/CD: beta → gamma → prod)
- SSM Parameter Store

## Common Commands

```bash
# Install all dependencies
make install

# Lint and format check (runs pnpm audit, prettier, eslint, pre-commit)
make check

# Auto-fix lint and format issues
make fix

# Run CDK/infrastructure tests (tsc + jest with cdk-nag)
make test

# CDK operations (stateless stack)
pnpm cdk-stateless synth
pnpm cdk-stateless ls
pnpm cdk-stateless deploy

# CDK operations (stateful stack)
pnpm cdk-stateful synth
pnpm cdk-stateful ls
pnpm cdk-stateful deploy
```
