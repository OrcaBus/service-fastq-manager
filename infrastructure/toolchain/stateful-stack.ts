import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DeploymentStackPipeline } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';
import { getStatefulApplicationStackProps } from '../stage/config';
import { REPO_NAME } from './constants';
import { StatefulApplicationStack } from '../stage/stateful-application-stack';

export class StatefulStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new DeploymentStackPipeline(this, 'StatefulFastqStackPipeline', {
      githubBranch: 'main',
      githubRepo: REPO_NAME,
      stack: StatefulApplicationStack,
      stackName: 'StatefulFastqStack',
      stackConfig: {
        beta: getStatefulApplicationStackProps('BETA'),
        gamma: getStatefulApplicationStackProps('GAMMA'),
        prod: getStatefulApplicationStackProps('PROD'),
      },
      pipelineName: 'StatefulFastqStackPipeline',
      cdkSynthCmd: ['pnpm install --frozen-lockfile --ignore-scripts', 'pnpm cdk-stateful synth'],
      enableSlackNotification: false,
    });
  }
}
