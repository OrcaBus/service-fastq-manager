import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DeploymentStackPipeline } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline';
import { getStatelessApplicationStackProps } from '../stage/config';
import { REPO_NAME } from './constants';
import { StatelessApplicationStack } from '../stage/stateless-application-stack';

export class StatelessStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new DeploymentStackPipeline(this, 'StatelessFastqStackPipeline', {
      githubBranch: 'main',
      githubRepo: REPO_NAME,
      stack: StatelessApplicationStack,
      stackName: 'StatelessFastqStack',
      stackConfig: {
        beta: getStatelessApplicationStackProps('BETA'),
        gamma: getStatelessApplicationStackProps('GAMMA'),
        prod: getStatelessApplicationStackProps('PROD'),
      },
      pipelineName: 'StatelessFastqStackPipeline',
      cdkSynthCmd: ['pnpm install --frozen-lockfile --ignore-scripts', 'pnpm cdk-stateless synth'],
      enableSlackNotification: false,
    });
  }
}
