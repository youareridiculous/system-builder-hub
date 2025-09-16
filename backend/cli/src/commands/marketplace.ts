import { Command } from '@oclif/core';
import { UI } from '../utils/ui';
import { SBHAPI } from '../utils/api';
import config from '../utils/config';

export default class Marketplace extends Command {
  static description = 'SBH Marketplace operations';

  static examples = [
    '$ sbh marketplace list',
    '$ sbh marketplace list --category "Sales & Ops"',
    '$ sbh marketplace launch flagship-crm',
    '$ sbh marketplace launch flagship-crm --name "My CRM"',
  ];

  static flags = {
    category: {
      char: 'c',
      description: 'Filter by category',
    },
    tags: {
      char: 't',
      description: 'Filter by tags (comma-separated)',
    },
    search: {
      char: 's',
      description: 'Search templates',
    },
    interactive: {
      char: 'i',
      description: 'Interactive mode',
      default: true,
    },
  };

  static args = [
    {
      name: 'action',
      description: 'Action to perform (list, launch)',
      required: true,
      options: ['list', 'launch'],
    },
    {
      name: 'template',
      description: 'Template slug for launch action',
      required: false,
    },
  ];

  async run() {
    const { flags, args } = await this.parse(Marketplace);
    const ui = new UI();

    try {
      // Check authentication
      const token = config.get('apiToken');
      if (!token) {
        ui.error('Not authenticated. Run "sbh login" first.');
        return;
      }

      const action = args.action;

      if (action === 'list') {
        await this.listTemplates(ui, flags);
      } else if (action === 'launch') {
        const templateSlug = args.template;
        if (!templateSlug) {
          ui.error('Template slug required for launch action');
          ui.info('Usage: sbh marketplace launch <template-slug>');
          return;
        }
        await this.launchTemplate(ui, templateSlug, flags);
      } else {
        ui.error(`Unknown action: ${action}`);
        ui.info('Available actions: list, launch');
      }

    } catch (error: any) {
      ui.error(error.message || 'Marketplace operation failed');
      this.exit(1);
    }
  }

  private async listTemplates(ui: UI, flags: any) {
    ui.startSpinner('Fetching templates...');

    try {
      const params: any = {};
      
      if (flags.category) {
        params.category = flags.category;
      }
      
      if (flags.tags) {
        params.tags = flags.tags.split(',');
      }
      
      if (flags.search) {
        params.search = flags.search;
      }

      const response = await SBHAPI.listTemplates(params);
      ui.stopSpinner(true, `Found ${response.data.length} templates`);

      if (response.data.length === 0) {
        ui.info('No templates found matching your criteria');
        return;
      }

      // Display templates in a table
      const tableData = response.data.map((template: any) => ({
        Name: template.attributes.name,
        Category: template.attributes.category || 'N/A',
        Tags: template.attributes.tags.slice(0, 3).join(', '),
        Badges: template.attributes.badges.slice(0, 2).join(', '),
        Version: template.attributes.version,
      }));

      ui.table(tableData);

      // Show categories if available
      if (response.meta?.categories) {
        console.log('\n📂 Available Categories:');
        response.meta.categories.forEach((category: string) => {
          console.log(`  - ${category}`);
        });
      }

    } catch (error: any) {
      ui.stopSpinner(false, 'Failed to fetch templates');
      ui.error(error.message || 'Failed to list templates');
    }
  }

  private async launchTemplate(ui: UI, templateSlug: string, flags: any) {
    ui.startSpinner('Fetching template details...');

    try {
      // Get template details
      const template = await SBHAPI.getTemplate(templateSlug);
      ui.stopSpinner(true, 'Template details fetched');

      ui.info(`🚀 Launching: ${template.data.attributes.name}`);
      ui.info(`Description: ${template.data.attributes.description}`);

      // Get launch parameters
      let tenantName = flags.name;
      let domain = flags.domain;
      let plan = flags.plan || 'starter';
      let seedDemoData = flags.seed !== false;

      if (flags.interactive) {
        tenantName = await ui.input('Tenant name:', `my-${templateSlug}`);
        domain = await ui.input('Domain (optional):', '');
        plan = await ui.select('Plan:', Object.keys(template.data.attributes.plans));
        seedDemoData = await ui.confirm('Seed demo data?', true);
      }

      // Validate tenant name
      if (!tenantName) {
        ui.error('Tenant name is required');
        return;
      }

      if (!/^[a-zA-Z0-9-_]+$/.test(tenantName)) {
        ui.error('Tenant name can only contain letters, numbers, hyphens, and underscores');
        return;
      }

      // Launch template
      ui.startSpinner('Launching template...');

      const launchData = {
        tenant_name: tenantName,
        domain: domain || undefined,
        plan,
        seed_demo_data: seedDemoData,
      };

      const result = await SBHAPI.launchTemplate(templateSlug, launchData);
      
      ui.stopSpinner(true, 'Template launched successfully');

      ui.success('🎉 Template launched successfully!');
      ui.info(`Tenant ID: ${result.data.attributes.tenant_id}`);
      ui.info(`Tenant Name: ${result.data.attributes.tenant_name}`);
      ui.info(`Template: ${result.data.attributes.template_name}`);

      if (result.data.attributes.onboarding_url) {
        ui.info(`Onboarding URL: ${result.data.attributes.onboarding_url}`);
      }

      if (result.data.attributes.admin_url) {
        ui.info(`Admin URL: ${result.data.attributes.admin_url}`);
      }

      // Open onboarding URL if available
      if (result.data.attributes.onboarding_url && flags.interactive) {
        const openBrowser = await ui.confirm('Open onboarding URL in browser?', true);
        if (openBrowser) {
          const { exec } = require('child_process');
          exec(`open "${result.data.attributes.onboarding_url}"`);
        }
      }

    } catch (error: any) {
      ui.stopSpinner(false, 'Failed to launch template');
      ui.error(error.response?.data?.errors?.[0]?.detail || error.message || 'Launch failed');
    }
  }
}
