import { Reference } from '../constants';

export interface SsmParameterPaths {
  referencePathsPrefix: string;
  sitesPathsPrefix: string;
}

export interface SsmParameterValues {
  referencePathsMap: Record<Reference, string>;
  sitesPathsMap: Record<Reference, string>;
}

export interface BuildSsmParameterProps {
  ssmParameterValues: SsmParameterValues;
  ssmParameterPaths: SsmParameterPaths;
}
