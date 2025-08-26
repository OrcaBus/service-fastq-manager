/*
Add in step functions
*/

// Imports
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import { LogLevel, StateMachineType } from 'aws-cdk-lib/aws-stepfunctions';
import { Construct } from 'constructs';
import * as path from 'path';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cdk from 'aws-cdk-lib';
import * as awsLogs from 'aws-cdk-lib/aws-logs';

// Local interfaces
import {
  SfnObject,
  SfnProps,
  SfnsProps,
  stepFunctionEcsMap,
  stepFunctionLambdaMap,
  stepFunctionNames,
  stepFunctionRequirementsMap,
} from './interfaces';
import { camelCaseToSnakeCase } from '../utils';
import {
  FASTQ_CACHE_PREFIX,
  FASTQ_MANAGER_STEP_FUNCTION_PREFIX,
  GZIP_FILE_SIZE_CALCULATION_SYNC,
  MAX_BASE_COUNT_READS,
  MAX_NTSM_READS,
  MAX_SEQUALI_READS,
  NTSM_BUCKET_PREFIX,
  ORA_DECOMPRESSION_REQUEST_SYNC,
  ORA_TO_RAW_MD5SUM_CALCULATION_SYNC,
  SEQUALI_HTML_PREFIX,
  SEQUALI_PARQUET_PREFIX,
  READ_COUNT_CALCULATION_SYNC,
  S3_DECOMPRESSION_PREFIX,
  STACK_SOURCE,
  STEP_FUNCTIONS_DIR,
  MULTIQC_PARQUET_PREFIX,
  MULTIQC_HTML_PREFIX,
  FASTQ_MULTIQC_CACHE_PREFIX,
} from '../constants';
import { NagSuppressions } from 'cdk-nag';
import { EcsContainerName } from '../ecs/interfaces';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';

/** Step Function stuff */
function createStateMachineDefinitionSubstitutions(props: SfnProps): {
  [key: string]: string;
} {
  const definitionSubstitutions: { [key: string]: string } = {};

  const sfnRequirements = stepFunctionRequirementsMap[props.stateMachineName];
  const lambdaFunctionNamesInSfn = stepFunctionLambdaMap[props.stateMachineName];
  const ecsContainerNamesInSfn = stepFunctionEcsMap[props.stateMachineName];
  const lambdaFunctions = props.lambdaObjects.filter((lambdaObject) =>
    lambdaFunctionNamesInSfn.includes(lambdaObject.lambdaName)
  );
  const ecsFargateConstructs = props.ecsFargateTasks.filter((fargateObject) =>
    ecsContainerNamesInSfn.includes(
      <EcsContainerName>fargateObject.containerDefinition.containerName
    )
  );

  /* Substitute lambdas in the state machine definition */
  for (const lambdaObject of lambdaFunctions) {
    const sfnSubtitutionKey = `__${camelCaseToSnakeCase(lambdaObject.lambdaName)}_lambda_function_arn__`;
    definitionSubstitutions[sfnSubtitutionKey] =
      lambdaObject.lambdaFunction.currentVersion.functionArn;
  }

  /* Add in fargate constructs */
  for (const fargateObject of ecsFargateConstructs) {
    const ecsContainerNameSnakeCase = camelCaseToSnakeCase(
      fargateObject.containerDefinition.containerName
    );
    definitionSubstitutions[`__${ecsContainerNameSnakeCase}_cluster_arn__`] =
      fargateObject.cluster.clusterArn;
    definitionSubstitutions[`__${ecsContainerNameSnakeCase}_task_definition_arn__`] =
      fargateObject.taskDefinition.taskDefinitionArn;
    definitionSubstitutions[`__${ecsContainerNameSnakeCase}_subnets__`] =
      fargateObject.cluster.vpc.privateSubnets.map((subnet) => subnet.subnetId).join(',');
    definitionSubstitutions[`__${ecsContainerNameSnakeCase}_security_group__`] =
      fargateObject.securityGroup.securityGroupId;
    definitionSubstitutions[`__${ecsContainerNameSnakeCase}_container_name__`] =
      fargateObject.containerDefinition.containerName;
  }

  /* If we need to push to the event bus, add in the event bus name and other substitutions */
  if (sfnRequirements.needsPutEventPermissions) {
    definitionSubstitutions['__event_bus_name__'] = props.eventBus.eventBusName;
    definitionSubstitutions['__stack_source__'] = STACK_SOURCE;
    definitionSubstitutions['__ora_to_raw_md5sum_calculation_detail_type__'] =
      ORA_TO_RAW_MD5SUM_CALCULATION_SYNC;
    definitionSubstitutions['__gzip_file_size_calculation_detail_type__'] =
      GZIP_FILE_SIZE_CALCULATION_SYNC;
    definitionSubstitutions['__ora_decompression_request_detail_type__'] =
      ORA_DECOMPRESSION_REQUEST_SYNC;
    definitionSubstitutions['__calculate_read_count_request_detail_type__'] =
      READ_COUNT_CALCULATION_SYNC;
  }

  /* We may need to put in this substitution even if we dont need access */
  definitionSubstitutions['__fastq_manager_cache_bucket__'] = props.fastqCacheBucket.bucketName;
  definitionSubstitutions['__fastq_manager_cache_prefix__'] = FASTQ_CACHE_PREFIX;
  definitionSubstitutions['__fastq_manager_multiqc_cache_prefix__'] = FASTQ_MULTIQC_CACHE_PREFIX;
  definitionSubstitutions['__fastq_manager_sequali_output_bucket__'] =
    props.sequaliBucket.bucketName;
  definitionSubstitutions['__fastq_manager_sequali_html_prefix__'] = SEQUALI_HTML_PREFIX;
  definitionSubstitutions['__fastq_manager_sequali_parquet_prefix__'] = SEQUALI_PARQUET_PREFIX;
  definitionSubstitutions['__fastq_manager_multiqc_html_prefix__'] = MULTIQC_HTML_PREFIX;
  definitionSubstitutions['__fastq_manager_multiqc_parquet_prefix__'] = MULTIQC_PARQUET_PREFIX;

  /*
      The SFN itself will not need read-write access to the ntsm bucket,
      So we cannot add in the if condition here
    */
  definitionSubstitutions['__ntsm_bucket__'] = props.ntsmCountBucket.bucketName;
  definitionSubstitutions['__ntsm_prefix__'] = NTSM_BUCKET_PREFIX;

  /* Add per step function specific substitutions */
  if (props.stateMachineName === 'runReadCountStats') {
    definitionSubstitutions['__max_base_count_reads__'] = MAX_BASE_COUNT_READS.toString();
  }

  if (props.stateMachineName === 'runQcStats') {
    definitionSubstitutions['__max_sequali_reads__'] = MAX_SEQUALI_READS.toString();
  }

  if (props.stateMachineName === 'runNtsmCount') {
    definitionSubstitutions['__max_ntsm_reads__'] = MAX_NTSM_READS.toString();
  }

  return definitionSubstitutions;
}

function wireUpStateMachinePermissions(props: SfnObject): void {
  /* Wire up lambda permissions */
  const sfnRequirements = stepFunctionRequirementsMap[props.stateMachineName];

  const lambdaFunctionNamesInSfn = stepFunctionLambdaMap[props.stateMachineName];
  const ecsContainerNamesInSfn = stepFunctionEcsMap[props.stateMachineName];
  const lambdaFunctions = props.lambdaObjects.filter((lambdaObject) =>
    lambdaFunctionNamesInSfn.includes(lambdaObject.lambdaName)
  );
  const ecsFargateConstructs = props.ecsFargateTasks.filter((fargateObject) =>
    ecsContainerNamesInSfn.includes(
      <EcsContainerName>fargateObject.containerDefinition.containerName
    )
  );

  /* Allow the state machine to invoke the lambda function */
  for (const lambdaObject of lambdaFunctions) {
    lambdaObject.lambdaFunction.currentVersion.grantInvoke(props.stateMachineObj);
  }

  if (sfnRequirements.needsEcsPermissions) {
    // Grant the state machine access to run the ECS tasks
    for (const ecsFargateConstruct of ecsFargateConstructs) {
      ecsFargateConstruct.taskDefinition.grantRun(props.stateMachineObj);
    }

    /* Grant the state machine access to monitor the tasks */
    props.stateMachineObj.addToRolePolicy(
      new iam.PolicyStatement({
        resources: [
          `arn:aws:events:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:rule/StepFunctionsGetEventsForECSTaskRule`,
        ],
        actions: ['events:PutTargets', 'events:PutRule', 'events:DescribeRule'],
      })
    );

    /* Will need cdk nag suppressions for this */
    NagSuppressions.addResourceSuppressions(
      props.stateMachineObj,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Need ability to put targets and rules for ECS task monitoring',
        },
      ],
      true
    );
  }

  if (sfnRequirements.needsPutEventPermissions) {
    props.eventBus.grantPutEventsTo(props.stateMachineObj);
  }

  if (sfnRequirements.needsFastqCacheS3BucketAccess) {
    props.fastqCacheBucket.grantRead(props.stateMachineObj, path.join(FASTQ_CACHE_PREFIX, '*'));

    // Will need cdk nag suppressions for this
    // Because we are using a wildcard for an IAM Resource policy
    NagSuppressions.addResourceSuppressions(
      props.stateMachineObj,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Need ability to read from S3 bucket with wildcard',
        },
      ],
      true
    );
  }

  if (sfnRequirements.needsDecompressionS3BucketAccess) {
    props.fastqDecompressionBucket.grantRead(
      props.stateMachineObj,
      path.join(S3_DECOMPRESSION_PREFIX, '*')
    );

    // Will need cdk nag suppressions for this
    // Because we are using a wildcard for an IAM Resource policy
    NagSuppressions.addResourceSuppressions(
      props.stateMachineObj,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Need ability to read from S3 bucket with wildcard',
        },
      ],
      true
    );
  }

  if (sfnRequirements.isExpressSfn) {
    // Will need cdk nag suppressions for this
    // Because we are using a wildcard for an IAM Resource policy
    NagSuppressions.addResourceSuppressions(
      props.stateMachineObj,
      [
        {
          id: 'AwsSolutions-IAM5',
          reason: 'Role permissions are required for the Express Step Function to run',
        },
      ],
      true
    );
  }
}

function buildStepFunction(scope: Construct, props: SfnProps): SfnObject {
  const sfnNameToSnakeCase = camelCaseToSnakeCase(props.stateMachineName);
  const sfnRequirements = stepFunctionRequirementsMap[props.stateMachineName];

  /* Create the state machine definition substitutions */
  const stateMachine = new sfn.StateMachine(scope, props.stateMachineName, {
    stateMachineName: `${FASTQ_MANAGER_STEP_FUNCTION_PREFIX}-${props.stateMachineName}`,
    definitionBody: sfn.DefinitionBody.fromFile(
      path.join(STEP_FUNCTIONS_DIR, sfnNameToSnakeCase + `_sfn_template.asl.json`)
    ),
    definitionSubstitutions: createStateMachineDefinitionSubstitutions(props),
    stateMachineType: sfnRequirements.isExpressSfn
      ? StateMachineType.EXPRESS
      : StateMachineType.STANDARD,
    logs: sfnRequirements.isExpressSfn
      ? // Enable logging on the state machine
        {
          level: LogLevel.ALL,
          // Create a new log group for the state machine
          destination: new awsLogs.LogGroup(scope, `${props.stateMachineName}-logs`, {
            retention: RetentionDays.ONE_DAY,
          }),
          includeExecutionData: true,
        }
      : undefined,
  });

  /* Grant the state machine permissions */
  wireUpStateMachinePermissions({
    stateMachineObj: stateMachine,
    ...props,
  });

  /* Nag Suppressions */
  /* AwsSolutions-SF1 - We don't need ALL events to be logged */
  /* AwsSolutions-SF2 - We also don't need X-Ray tracing */
  NagSuppressions.addResourceSuppressions(
    stateMachine,
    [
      {
        id: 'AwsSolutions-SF1',
        reason: 'We do not need all events to be logged',
      },
      {
        id: 'AwsSolutions-SF2',
        reason: 'We do not need X-Ray tracing',
      },
    ],
    true
  );

  /* Return as a state machine object property */
  return {
    ...props,
    stateMachineObj: stateMachine,
  };
}

export function buildAllStepFunctions(scope: Construct, props: SfnsProps): SfnObject[] {
  // Initialize the step function objects
  const sfnObjects = [] as SfnObject[];

  // Iterate over lambdaLayerToMapping and create the lambda functions
  for (const sfnName of stepFunctionNames) {
    sfnObjects.push(
      buildStepFunction(scope, {
        stateMachineName: sfnName,
        ...props,
      })
    );
  }

  return sfnObjects;
}
