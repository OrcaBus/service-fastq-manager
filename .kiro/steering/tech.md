# Tech Stack & Build System

## Infrastructure (Root Project)

- **Language**: TypeScript (ES2020 target, strict mode)
- **IaC**: AWS CDK v2 with `@orcabus/platform-cdk-constructs`
- **Package Manager**: pnpm (v11.7.0, managed via Corepack)
- **Node**: v22.x
- **Testing**: Jest with ts-jest
- **Linting**: ESLint (flat config), Prettier
- **Pre-commit**: pre-commit hooks (trailing whitespace, secrets detection, eslint, prettier)
- **CI**: GitHub Actions (lint/security checks + CDK nag tests on PRs)

## Application (app/ directory)

- **API**: Python, FastAPI + Mangum (Lambda adapter)
- **Data Models**: Pydantic v2 with `dyntastic` (DynamoDB ORM)
- **Database**: DynamoDB (three tables: Fastq, FastqSet, Jobs)
- **Lambdas**: Python (individual handler files, one per lambda directory)
- **ECS Tasks**: Dockerized (bioinformatics tools for md5sum, read counting, NTSM, sequali, somalier)
- **Orchestration**: AWS Step Functions (ASL JSON templates)
- **Events**: Amazon EventBridge

## Key Libraries

| Layer | Library                            | Purpose                       |
| ----- | ---------------------------------- | ----------------------------- |
| API   | `fastapi`                          | REST framework                |
| API   | `mangum`                           | Lambda/APIGW adapter          |
| API   | `dyntastic`                        | DynamoDB ORM (Pydantic-based) |
| API   | `pydantic` v2                      | Data validation/serialization |
| API   | `ulid-py`                          | ULID generation               |
| IaC   | `aws-cdk-lib`                      | Infrastructure definitions    |
| IaC   | `@aws-cdk/aws-lambda-python-alpha` | Python Lambda bundling        |
| IaC   | `@orcabus/platform-cdk-constructs` | Shared OrcaBus constructs     |

## Common Commands

```sh
# Install all dependencies
make install

# Run linting and formatting checks
make check

# Auto-fix lint/formatting issues
make fix

# Run CDK/infrastructure tests (Jest + cdk-nag)
make test
# or
pnpm test

# CDK deployment commands
pnpm cdk-stateless synth    # Synthesize stateless stack
pnpm cdk-stateful synth     # Synthesize stateful stack
pnpm cdk-stateless deploy   # Deploy stateless resources
pnpm cdk-stateful deploy    # Deploy stateful resources
pnpm cdk-stateless ls       # List stateless stacks
pnpm cdk-stateful ls        # List stateful stacks
```

## Code Style

- **TypeScript**: Prettier (2-space indent, single quotes, trailing commas ES5, 100 char line width, semicolons)
- **Python (API)**: snake_case for internal models, camelCase for API responses (serialization handled by Pydantic alias generators)
- **Python (Lambdas)**: Simple handler functions with explicit input validation via dict key checks
