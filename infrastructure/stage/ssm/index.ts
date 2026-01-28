import { Construct } from 'constructs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import { BuildSsmParameterProps } from './interfaces';

import * as path from 'path';

export function buildSsmParameters(scope: Construct, props: BuildSsmParameterProps) {
  /**
   * SSM Stack here
   *
   * */

  /**
   * Reference Paths
   */
  // Reference configuration map
  for (const [key, value] of Object.entries(props.ssmParameterValues.referencePathsMap)) {
    new ssm.StringParameter(scope, `reference-paths-${key}`, {
      parameterName: path.join(props.ssmParameterPaths.referencePathsPrefix, key),
      stringValue: value,
    });
  }

  // Sites map
  for (const [key, value] of Object.entries(props.ssmParameterValues.sitesPathsMap)) {
    new ssm.StringParameter(scope, `sites-paths-${key}`, {
      parameterName: path.join(props.ssmParameterPaths.sitesPathsPrefix, key),
      stringValue: value,
    });
  }
}
