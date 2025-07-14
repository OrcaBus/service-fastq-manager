/*
Build the ecs fargate task
*/

import { Construct } from 'constructs';
import {
  CPU_ARCHITECTURE_MAP,
  EcsFargateTaskConstruct,
  FargateEcsTaskConstructProps,
} from '@orcabus/platform-cdk-constructs/ecs';
import * as path from 'path';
import {
  BYOB_ICAV2_PREFIX,
  ECS_DIR,
  FASTQ_CACHE_PREFIX,
  NTSM_BUCKET_PREFIX,
  S3_DECOMPRESSION_PREFIX,
} from '../constants';
import {
  BuildFastqFargateEcsProps,
  BuildFastqFargateTasks,
  ecsContainerNameList,
  ecsContainerNameToRequirementsMap,
} from './interfaces';
import { NagSuppressions } from 'cdk-nag';
import { camelCaseToSnakeCase } from '../utils';

function buildEcsFargateTask(scope: Construct, id: string, props: FargateEcsTaskConstructProps) {
  /*
      Generate an ECS Fargate task construct with the provided properties.
      */
  return new EcsFargateTaskConstruct(scope, id, props);
}

function buildFargateTask(
  scope: Construct,
  props: BuildFastqFargateEcsProps
): EcsFargateTaskConstruct {
  /*
      Build the Fargate task.

      We use 8 CPUs for each task, as we want the network speed up and the gzip will use the threads.
      The containerName will be set to the container name
      and the docker path can be found under ECS_DIR / camelCaseToSnakeCase(props.containerName)
      */

  const ecsTask = buildEcsFargateTask(scope, props.containerName, {
    containerName: props.containerName,
    dockerPath: path.join(ECS_DIR, camelCaseToSnakeCase(props.containerName)),
    nCpus: 8, // 8 CPUs
    memoryLimitGiB: 16, // 16 GB of memory (minimum for 8 CPUs)
    architecture: 'ARM64',
    runtimePlatform: CPU_ARCHITECTURE_MAP['ARM64'],
  });

  // Get the permissions for the task
  const ecsPermissions = ecsContainerNameToRequirementsMap[props.containerName];

  // NTSM Count task will need to write out to the NTSM bucket
  if (ecsPermissions.needsNtsmBucketAccess) {
    props.ntsmS3Bucket.grantReadWrite(
      ecsTask.taskDefinition.taskRole,
      path.join(NTSM_BUCKET_PREFIX, '*')
    );
  }

  // Fastq Cache bucket access required for stats jobs
  // Since the ecs task will write out to the cache bucket
  // To be picked up by the proceeding step functions task
  if (ecsPermissions.needsFastqCacheBucketAccess) {
    props.fastqCacheS3Bucket.grantReadWrite(
      ecsTask.taskDefinition.taskRole,
      path.join(FASTQ_CACHE_PREFIX, '*')
    );
  }

  // Fastq Decompression bucket access required for jobs where we outsource the
  // decompression step to the decompression service first and then
  // write the decompressed files to the fastq cache bucket.
  // Since the ecs task will write out to the decompression bucket
  if (ecsPermissions.needsFastqDecompressionBucketAccess) {
    props.fastqDecompressionS3Bucket.grantRead(
      ecsTask.taskDefinition.taskRole,
      path.join(S3_DECOMPRESSION_PREFIX, '*')
    );
  }

  // Pipeline Cache bucket access
  // Needed since inputs may already be in gz format
  // In which case they will be in the pipeline cache bucket
  // This is rare, since we output ORA by default now.
  if (ecsPermissions.needsPipelineCacheBucketReadAccess) {
    props.pipelineCacheS3Bucket.grantRead(
      ecsTask.taskDefinition.taskRole,
      path.join(BYOB_ICAV2_PREFIX, '*')
    );
  }

  // Add suppressions for the task role
  // Since the task role needs to access the S3 bucket prefix
  NagSuppressions.addResourceSuppressions(
    [ecsTask.taskDefinition, ecsTask.taskExecutionRole],
    [
      {
        id: 'AwsSolutions-IAM5',
        reason:
          'The task role needs to access the S3 bucket and secrets manager for decompression and metadata storage.',
      },
      {
        id: 'AwsSolutions-IAM4',
        reason:
          'We use the standard ecs task role for this task, which allows the guard duty agent to run alongside the task.',
      },
      {
        id: 'AwsSolutions-ECS2',
        reason:
          'The task is designed to run with some constant environment variables, not sure why this is a bad thing?',
      },
    ],
    true
  );

  return ecsTask;
}

export function buildFargateTasks(
  scope: Construct,
  props: BuildFastqFargateTasks
): EcsFargateTaskConstruct[] {
  const ecsFargateContainerList: EcsFargateTaskConstruct[] = [];
  for (const containerName of ecsContainerNameList) {
    ecsFargateContainerList.push(
      buildFargateTask(scope, {
        containerName: containerName,
        ...props,
      })
    );
  }
  return ecsFargateContainerList;
}
