import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';
import { StatelessApplicationStackConfig } from './interfaces';
import { buildAllLambdaFunctions } from './lambdas';
import { buildFargateTasks } from './ecs';
import { buildAllStepFunctions } from './step-functions';
import {
  addHttpRoutes,
  buildApiGateway,
  buildApiIntegration,
  buildApiInterfaceLambda,
} from './api';

export type StatelessApplicationStackProps = cdk.StackProps & StatelessApplicationStackConfig;

export class StatelessApplicationStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: StatelessApplicationStackProps) {
    super(scope, id, props);

    /**
     * Stateless Application stack components
     * Build all the lambdas
     * Build the ECS tasks
     * Build the Step functions
     * Build the API Gateway
     */

    // Part 0 - import the necessary names as objects
    const eventBusObj = events.EventBus.fromEventBusName(
      this,
      props.eventBusName,
      props.eventBusName
    );

    // SSM Parameter for the hosted zone (we use to get the domain name)
    const hostedZoneSsmParameter = ssm.StringParameter.fromStringParameterName(
      this,
      props.hostedZoneSsmParameterName,
      props.hostedZoneSsmParameterName
    );

    // S3 Buckets
    const ntsmBucketObj = s3.Bucket.fromBucketName(
      this,
      props.ntsmBucketName,
      props.ntsmBucketName
    );
    const sequaliBucketObj = s3.Bucket.fromBucketName(
      this,
      props.fastqSequaliBucketName,
      props.fastqSequaliBucketName
    );
    const fastqManagerCacheBucketObj = s3.Bucket.fromBucketName(
      this,
      props.fastqManagerCacheBucketName,
      props.fastqManagerCacheBucketName
    );
    const fastqDecompressionBucketObj = s3.Bucket.fromBucketName(
      this,
      props.fastqDecompressionBucketName,
      props.fastqDecompressionBucketName
    );
    const pipelineCacheBucketObj = s3.Bucket.fromBucketName(
      this,
      props.pipelineCacheBucketName,
      props.pipelineCacheBucketName
    );

    // DynamoDB Tables
    const fastqApiTableObj = dynamodb.TableV2.fromTableName(
      this,
      props.fastqApiTableName,
      props.fastqApiTableName
    );
    const fastqSetApiTableObj = dynamodb.TableV2.fromTableName(
      this,
      props.fastqSetApiTableName,
      props.fastqSetApiTableName
    );
    const fastqJobApiTableObj = dynamodb.TableV2.fromTableName(
      this,
      props.fastqJobApiTableName,
      props.fastqJobApiTableName
    );
    const multiqcJobsTableObj = dynamodb.TableV2.fromTableName(
      this,
      props.multiqcJobApiTableName,
      props.multiqcJobApiTableName
    );

    // Part 1 - build the lambdas
    const lambdaObjList = buildAllLambdaFunctions(this, {
      jobsTable: fastqJobApiTableObj,
      sequaliBucket: sequaliBucketObj,
      fastqCacheBucket: fastqManagerCacheBucketObj,
      ntsmBucket: ntsmBucketObj,
      fastqDecompressionBucket: fastqDecompressionBucketObj,
    });

    // Part 2 - build the ecs tasks
    const ecsTaskList = buildFargateTasks(this, {
      fastqCacheS3Bucket: fastqManagerCacheBucketObj,
      fastqDecompressionS3Bucket: fastqDecompressionBucketObj,
      fastqSequaliS3Bucket: sequaliBucketObj,
      ntsmS3Bucket: ntsmBucketObj,
      pipelineCacheS3Bucket: pipelineCacheBucketObj,
    });

    // Part 3 - build the step functions
    const sfnObjList = buildAllStepFunctions(this, {
      lambdaObjects: lambdaObjList,
      eventBus: eventBusObj,
      ecsFargateTasks: ecsTaskList,
      fastqCacheBucket: fastqManagerCacheBucketObj,
      ntsmCountBucket: ntsmBucketObj,
      sequaliBucket: sequaliBucketObj,
      fastqDecompressionBucket: fastqDecompressionBucketObj,
    });

    /*
    Part 4: API Gateway for the stateless application
    */
    // Build the API Gateway
    const lambdaApi = buildApiInterfaceLambda(this, {
      lambdaName: 'fastqManagerApi',
      fastqTable: fastqApiTableObj,
      fastqSetTable: fastqSetApiTableObj,
      jobsTable: fastqJobApiTableObj,
      stepFunctions: sfnObjList,
      eventBus: eventBusObj,
      hostedZoneSsmParameter: hostedZoneSsmParameter,
      multiqcJobsTable: multiqcJobsTableObj,
    });
    const apiGateway = buildApiGateway(this, props.apiGatewayCognitoProps);
    const apiIntegration = buildApiIntegration({
      lambdaFunction: lambdaApi,
    });
    addHttpRoutes(this, {
      apiGateway: apiGateway,
      apiIntegration: apiIntegration,
    });
  }
}
