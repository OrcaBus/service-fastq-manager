export function camelCaseToSnakeCase(camelCase: string): string {
  return camelCase.replace(/([A-Z])/g, '_$1').toLowerCase();
}

export function camelCaseToKebabCase(camelCase: string): string {
  return camelCase.replace(/([a-z0-9])([A-Z])/g, '$1-$2').toLowerCase();
}
