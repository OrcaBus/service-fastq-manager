import { App } from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { StatefulApplicationStack } from '../infrastructure/stage/stateful-application-stack';
import { getStatefulApplicationStackProps } from '../infrastructure/stage/config';
import { PROD_ENVIRONMENT } from '@orcabus/platform-cdk-constructs/deployment-stack-pipeline/config';

describe('Event Schemas CDK Synthesis', () => {
  let template: Template;

  beforeAll(() => {
    const app = new App({});
    const stack = new StatefulApplicationStack(app, 'TestStatefulStack', {
      ...getStatefulApplicationStackProps('PROD'),
      env: PROD_ENVIRONMENT,
    });
    template = Template.fromStack(stack);
  });

  describe('AWS::EventSchemas::Schema resources', () => {
    test('stateful stack contains exactly 3 schema resources', () => {
      template.resourceCountIs('AWS::EventSchemas::Schema', 3);
    });

    test.each([
      ['fastqStateChange', 'fastq-manager--fastqStateChange--2025.06.04'],
      ['fastqSetStateChange', 'fastq-manager--fastqSetStateChange--2025.06.04'],
      ['fastqMultiqcJobStateChange', 'fastq-manager--fastqMultiqcJobStateChange--2025.06.04'],
    ])('schema %s is registered with correct naming pattern', (_schemaName, expectedSchemaName) => {
      template.hasResourceProperties('AWS::EventSchemas::Schema', {
        RegistryName: 'orcabus.events',
        SchemaName: expectedSchemaName,
        Type: 'JSONSchemaDraft4',
      });
    });
  });

  describe('AWS::SSM::Parameter resources for schema discovery', () => {
    test.each([['fastqStateChange'], ['fastqSetStateChange'], ['fastqMultiqcJobStateChange']])(
      'SSM parameter for %s registry-name exists with correct value',
      (schemaName) => {
        template.hasResourceProperties('AWS::SSM::Parameter', {
          Name: `/orcabus/services/fastq-manager/event-schemas/${schemaName}/registry-name`,
          Value: 'orcabus.events',
        });
      }
    );

    test.each([
      ['fastqStateChange', 'fastq-manager--fastqStateChange--2025.06.04'],
      ['fastqSetStateChange', 'fastq-manager--fastqSetStateChange--2025.06.04'],
      ['fastqMultiqcJobStateChange', 'fastq-manager--fastqMultiqcJobStateChange--2025.06.04'],
    ])(
      'SSM parameter for %s schema-name exists with correct value',
      (schemaName, expectedValue) => {
        template.hasResourceProperties('AWS::SSM::Parameter', {
          Name: `/orcabus/services/fastq-manager/event-schemas/${schemaName}/schema-name`,
          Value: expectedValue,
        });
      }
    );

    test.each([['fastqStateChange'], ['fastqSetStateChange'], ['fastqMultiqcJobStateChange']])(
      'SSM parameter for %s payload-version exists with correct value',
      (schemaName) => {
        template.hasResourceProperties('AWS::SSM::Parameter', {
          Name: `/orcabus/services/fastq-manager/event-schemas/${schemaName}/payload-version`,
          Value: '2025.06.04',
        });
      }
    );
  });
});
