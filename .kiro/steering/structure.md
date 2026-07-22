# Project Structure

```
service-fastq-manager/
├── bin/deploy.ts                    # CDK app entry point (stateless/stateful context switch)
├── infrastructure/                  # AWS CDK infrastructure code (TypeScript)
│   ├── toolchain/                   # CodePipeline stacks for cross-env deployment
│   │   ├── stateless-stack.ts
│   │   └── stateful-stack.ts
│   └── stage/                       # Per-environment resource definitions
│       ├── config.ts                # Environment-specific configuration
│       ├── constants.ts             # Shared constants (table names, bucket names)
│       ├── interfaces.ts            # Stack prop interfaces
│       ├── stateful-application-stack.ts
│       ├── stateless-application-stack.ts
│       ├── api/                     # API Gateway construct
│       ├── dynamodb/                # DynamoDB table definitions
│       ├── ecs/                     # ECS task definitions
│       ├── lambdas/                 # Lambda construct definitions
│       ├── s3/                      # S3 bucket constructs
│       ├── ssm/                     # SSM parameter constructs
│       ├── step-functions/          # Step Function constructs
│       └── utils/                   # Shared infrastructure utilities
├── app/                             # Application code (Python)
│   ├── api/                         # FastAPI REST API (deployed as Lambda)
│   │   ├── handler.py              # Lambda entry point (Mangum wrapper)
│   │   ├── requirements.txt        # Python runtime dependencies
│   │   ├── requirements-test.txt   # Python test dependencies
│   │   ├── tests/                  # API unit tests
│   │   └── fastq_manager_api_tools/  # API package
│   │       ├── api/v1/routers/     # FastAPI route handlers
│   │       ├── models/             # Pydantic/Dyntastic data models
│   │       ├── events/             # EventBridge event publishing
│   │       ├── cache.py            # In-memory S3 object cache
│   │       ├── globals.py          # Constants and env var names
│   │       └── utils.py            # Shared utilities (ULID, serialization)
│   ├── lambdas/                    # Individual Lambda handlers (zip-based Python + container image)
│   │   ├── {function_name}_py/     # ZIP-based Python Lambda (handler file)
│   │   │   └── {function_name}.py  # Handler file
│   │   └── {function_name}_docker/ # Container-image Lambda (Dockerfile + entrypoint script)
│   │       ├── Dockerfile
│   │       └── {function_name}.py
│   ├── ecs/                        # Dockerized ECS tasks
│   │   └── {task_name}/            # One directory per ECS task
│   │       ├── Dockerfile
│   │       └── docker-entrypoint.sh
│   └── step-functions-templates/   # Step Function ASL definitions (.asl.json)
├── test/                           # CDK infrastructure tests (cdk-nag compliance)
├── docs/                           # Operational docs, SOPs, usage examples
└── .github/workflows/              # CI pipeline (PR tests)
```

## Conventions

- **Lambda naming**: Most handler directories end with the `_py` suffix and contain a single `{function_name}.py`; container-image Lambdas use an `_docker` suffix and include a `Dockerfile` plus the Python entry script.
- **ECS tasks**: Each task is a self-contained Docker image with its own `Dockerfile` and `docker-entrypoint.sh`.
- **Step Functions**: Defined as ASL JSON templates in `app/step-functions-templates/`, referenced by CDK constructs.
- **CDK split**: `stateful` stacks contain DynamoDB tables, S3 buckets; `stateless` stacks contain Lambdas, Step Functions, API Gateway, ECS.
- **Deployment**: CodePipeline deploys to `beta` → `gamma` → `prod` environments.
- **Tests**: CDK tests live in `./test/`, API tests in `./app/api/tests/`. Tests run alongside business logic directories.
