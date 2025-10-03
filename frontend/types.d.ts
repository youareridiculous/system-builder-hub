export interface RuntimeConfig {
  baseUrl: string;
  auth?: { type: 'bearer'; localStorageKey?: string };
  queryParams?: Record<string, string | number | boolean>;
  resources: ResourceConfig[];
}

export interface ResourceConfig {
  name: string;
  label?: string;
  idKey?: string;
  columns?: Array<{ key: string; label?: string }>;
  fields?: Array<FormField>;
}

export type FormField =
  | { name: string; label?: string; type?: 'text'; required?: boolean; minLength?: number; maxLength?: number }
  | { name: string; label?: string; type: 'number'; required?: boolean }
  | { name: string; label?: string; type: 'date'; required?: boolean }
  | { name: string; label?: string; type: 'select'; options: Array<{ value: string | number; label: string }>; required?: boolean }
  | { name: string; label?: string; type: 'textarea'; required?: boolean };

