# Project Structure

The root is an AWS CDK project. Application logic lives in `./app`. Infrastructure code lives in `./infrastructure`.

```
├── bin/deploy.ts                         # CDK app entry point (stateless vs stateful via context)
├── infrastructure/
│   ├── toolchain/                        # CodePipeline stacks for cross-environment deployment
│   │   ├── stateless-stack.ts
│   │   ├── stateful-stack.ts
│   │   └── constants.ts                  # Repo name, pipeline config
│   └── stage/                            # Application stack definitions
│       ├── config.ts                     # Per-environment (beta/gamma/prod) configuration
│       ├── constants.ts                  # All constants: table names, bucket names, event constants
│       ├── interfaces.ts                 # TypeScript interfaces for stack props
│       ├── stateless-application-stack.ts # Main stateless stack (Lambdas, ECS, SFN, API GW)
│       ├── stateful-application-stack.ts  # Stateful stack (DynamoDB, S3)
│       ├── api/                          # API Gateway CDK constructs
│       ├── dynamodb/                     # DynamoDB table definitions
│       ├── ecs/                          # ECS Fargate task CDK constructs
│       ├── lambdas/                      # Lambda function CDK constructs + interfaces
│       ├── s3/                           # S3 bucket CDK constructs
│       ├── ssm/                          # SSM parameter CDK constructs
│       ├── step-functions/               # Step Function CDK constructs
│       └── utils/                        # CDK utility functions (e.g., camelCase to snake_case)
├── app/
│   ├── api/                              # FastAPI application (runs as Lambda via Mangum)
│   │   ├── handler.py                    # FastAPI app definition + Mangum Lambda handler
│   │   ├── fastq_manager_api_tools/      # Main API package
│   │   │   ├── api/v1/routers/           # Route handlers (fastq, fastq_set, rgid, multiqc)
│   │   │   ├── models/                   # Pydantic/Dyntastic data models
│   │   │   ├── events/                   # EventBridge event publishing
│   │   │   ├── cache.py                  # S3 object caching logic
│   │   │   ├── globals.py                # Global constants (env vars, prefixes)
│   │   │   └── utils.py                  # Shared utilities (ULID, datetime, case conversion)
│   │   ├── tests/                        # API integration tests (pytest + httpx)
│   │   ├── requirements.txt              # Production Python dependencies
│   │   └── requirements-test.txt         # Test Python dependencies
│   ├── lambdas/                          # Individual Lambda function handlers
│   │   ├── {name}_py/                    # Python UV-packaged Lambdas (snake_case)
│   │   └── {name}_docker/                # Docker-based Lambdas (snake_case)
│   ├── ecs/                              # ECS Fargate task containers
│   │   └── {task_name}/                  # Each task has Dockerfile + docker-entrypoint.sh
│   └── step-functions-templates/         # ASL JSON definitions for state machines
├── test/                                 # CDK nag compliance tests (Jest)
├── docs/                                 # Operational documentation and SOPs
├── Makefile                              # Top-level build commands
├── package.json                          # Node dependencies and scripts
├── tsconfig.json                         # TypeScript compiler config
└── .pre-commit-config.yaml               # Pre-commit hook configuration
```

## Key Conventions

- **Stateful vs Stateless separation**: Resources that hold data (DynamoDB, S3) are in stateful stacks; compute resources (Lambda, ECS, SFN, API GW) are in stateless stacks
- **Lambda naming**: CDK uses camelCase names, directories use snake_case with `_py` or `_docker` suffix
- **ECS task naming**: Directories use snake_case (e.g., `get_read_count/`)
- **Model variants**: Pydantic models use suffixes — `Data` (DB), `Response` (API), `Create` (input), `Patch` (partial update)
- **API routing**: Versioned prefix `/api/v1`, action PATCHes use colon syntax (`:runQcStats`), attribute PATCHes use path segments (`/addQcStats`)
- **Builder functions**: Infrastructure uses `buildAll*()` and `build*()` factory functions
- **Constants centralization**: All infrastructure constants live in `infrastructure/stage/constants.ts`
