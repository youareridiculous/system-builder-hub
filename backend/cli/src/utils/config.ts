import Conf from 'conf';
import { homedir } from 'os';
import { join } from 'path';

export interface SBHConfig {
  apiToken?: string;
  apiUrl?: string;
  tenantId?: string;
  defaultTemplate?: string;
  lastLogin?: string;
}

const config = new Conf<SBHConfig>({
  projectName: 'sbh-cli',
  schema: {
    apiToken: {
      type: 'string',
      default: undefined,
    },
    apiUrl: {
      type: 'string',
      default: 'http://localhost:5001',
    },
    tenantId: {
      type: 'string',
      default: undefined,
    },
    defaultTemplate: {
      type: 'string',
      default: 'flagship-crm',
    },
    lastLogin: {
      type: 'string',
      default: undefined,
    },
  },
});

export default config;
