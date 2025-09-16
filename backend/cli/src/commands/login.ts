import { Command } from '@oclif/core';
import { UI } from '../utils/ui';
import { SBHAPI } from '../utils/api';
import config from '../utils/config';

export default class Login extends Command {
  static description = 'Authenticate to SBH Marketplace (API token)';

  static examples = [
    '$ sbh login',
    '$ sbh login --token your-api-token',
    '$ sbh login --email user@example.com',
  ];

  static flags = {
    token: {
      char: 't',
      description: 'API token for authentication',
    },
    email: {
      char: 'e',
      description: 'Email for interactive login',
    },
    apiUrl: {
      char: 'u',
      description: 'SBH API URL',
      default: 'http://localhost:5001',
    },
  };

  async run() {
    const { flags } = await this.parse(Login);
    const ui = new UI();

    try {
      ui.info('🔐 SBH Authentication');
      ui.info('====================');

      // Set API URL if provided
      if (flags.apiUrl) {
        config.set('apiUrl', flags.apiUrl);
        ui.info(`API URL set to: ${flags.apiUrl}`);
      }

      let token = flags.token;

      // If no token provided, prompt for credentials
      if (!token) {
        const email = flags.email || await ui.input('Email:');
        const password = await ui.password('Password:');

        ui.startSpinner('Authenticating...');

        try {
          const response = await SBHAPI.login({ email, password });
          token = response.token || response.access_token;
          
          if (!token) {
            ui.stopSpinner(false, 'Authentication failed');
            ui.error('No token received from server');
            return;
          }

          ui.stopSpinner(true, 'Authentication successful');
        } catch (error: any) {
          ui.stopSpinner(false, 'Authentication failed');
          ui.error(error.response?.data?.message || error.message || 'Login failed');
          return;
        }
      }

      // Validate token by getting profile
      ui.startSpinner('Validating token...');
      
      try {
        // Temporarily set token for validation
        const originalToken = config.get('apiToken');
        config.set('apiToken', token);
        
        const profile = await SBHAPI.getProfile();
        
        ui.stopSpinner(true, 'Token validated');
        
        // Save token and profile info
        config.set('apiToken', token);
        config.set('lastLogin', new Date().toISOString());
        
        if (profile.tenant_id) {
          config.set('tenantId', profile.tenant_id);
        }

        ui.success('Successfully logged in to SBH!');
        ui.info(`User: ${profile.email || profile.name || 'Unknown'}`);
        if (profile.tenant_id) {
          ui.info(`Tenant: ${profile.tenant_id}`);
        }
        ui.info(`API URL: ${config.get('apiUrl')}`);

      } catch (error: any) {
        ui.stopSpinner(false, 'Token validation failed');
        ui.error('Invalid or expired token');
        return;
      }

    } catch (error: any) {
      ui.error(error.message || 'Login failed');
      this.exit(1);
    }
  }
}
