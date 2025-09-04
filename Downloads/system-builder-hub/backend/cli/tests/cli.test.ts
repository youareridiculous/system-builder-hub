import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { SBHAPI } from '../src/utils/api';
import { UI } from '../src/utils/ui';
import config from '../src/utils/config';

// Mock dependencies
jest.mock('axios');
jest.mock('conf');

describe('SBH CLI', () => {
  let api: SBHAPI;
  let ui: UI;

  beforeEach(() => {
    api = new SBHAPI();
    ui = new UI();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Authentication', () => {
    it('should authenticate with valid credentials', async () => {
      const mockResponse = {
        token: 'valid-token',
        user: {
          id: 'user-123',
          email: 'test@example.com',
          name: 'Test User',
          role: 'admin',
          tenant_id: 'tenant-456'
        }
      };

      jest.spyOn(api, 'login').mockResolvedValue(mockResponse);
      jest.spyOn(api, 'getProfile').mockResolvedValue(mockResponse.user);

      const result = await api.login({
        email: 'test@example.com',
        password: 'password'
      });

      expect(result).toEqual(mockResponse);
    });

    it('should handle authentication failure', async () => {
      jest.spyOn(api, 'login').mockRejectedValue(new Error('Invalid credentials'));

      await expect(api.login({
        email: 'test@example.com',
        password: 'wrong-password'
      })).rejects.toThrow('Invalid credentials');
    });
  });

  describe('Template Management', () => {
    it('should list templates', async () => {
      const mockTemplates = {
        data: [
          {
            id: 'flagship-crm',
            type: 'template',
            attributes: {
              name: 'Flagship CRM & Ops',
              description: 'Complete CRM system',
              category: 'Sales & Ops',
              tags: ['crm', 'sales'],
              badges: ['Multi-tenant', 'AI'],
              version: '1.0.0'
            }
          }
        ],
        meta: {
          total: 1,
          categories: ['Sales & Ops'],
          tags: ['crm', 'sales']
        }
      };

      jest.spyOn(api, 'listTemplates').mockResolvedValue(mockTemplates);

      const result = await api.listTemplates();
      expect(result).toEqual(mockTemplates);
      expect(result.data).toHaveLength(1);
      expect(result.data[0].attributes.name).toBe('Flagship CRM & Ops');
    });

    it('should get template details', async () => {
      const mockTemplate = {
        data: {
          id: 'flagship-crm',
          type: 'template',
          attributes: {
            name: 'Flagship CRM & Ops',
            description: 'Complete CRM system',
            features: ['Contact Management', 'Deal Pipeline'],
            plans: {
              starter: { name: 'Starter', price: 0 },
              pro: { name: 'Pro', price: 49 }
            }
          }
        }
      };

      jest.spyOn(api, 'getTemplate').mockResolvedValue(mockTemplate);

      const result = await api.getTemplate('flagship-crm');
      expect(result).toEqual(mockTemplate);
      expect(result.data.attributes.name).toBe('Flagship CRM & Ops');
    });

    it('should launch template', async () => {
      const mockLaunch = {
        data: {
          id: 'tenant-123',
          type: 'tenant_launch',
          attributes: {
            tenant_id: 'tenant-123',
            template_slug: 'flagship-crm',
            tenant_name: 'My CRM',
            status: 'created',
            onboarding_url: '/ui/onboarding?tenant_id=tenant-123'
          }
        }
      };

      jest.spyOn(api, 'launchTemplate').mockResolvedValue(mockLaunch);

      const result = await api.launchTemplate('flagship-crm', {
        tenant_name: 'My CRM',
        plan: 'starter',
        seed_demo_data: true
      });

      expect(result).toEqual(mockLaunch);
      expect(result.data.attributes.tenant_name).toBe('My CRM');
    });
  });

  describe('Meta-Builder', () => {
    it('should create scaffold plan', async () => {
      const mockPlan = {
        data: {
          id: 'plan-123',
          type: 'scaffold_plan',
          attributes: {
            goal_text: 'Build a CRM system',
            entities: ['contacts', 'deals', 'companies'],
            apis: ['/api/contacts', '/api/deals'],
            ui_modules: ['contacts', 'deals'],
            status: 'draft'
          }
        }
      };

      jest.spyOn(api, 'createScaffoldPlan').mockResolvedValue(mockPlan);

      const result = await api.createScaffoldPlan({
        goal_text: 'Build a CRM system',
        mode: 'guided'
      });

      expect(result).toEqual(mockPlan);
      expect(result.data.attributes.entities).toContain('contacts');
    });

    it('should build scaffold', async () => {
      const mockBuild = {
        data: {
          id: 'build-123',
          type: 'scaffold_build',
          attributes: {
            session_id: 'session-123',
            plan_id: 'plan-123',
            status: 'completed',
            artifacts: ['zip', 'github']
          }
        }
      };

      jest.spyOn(api, 'buildScaffold').mockResolvedValue(mockBuild);

      const result = await api.buildScaffold({
        session_id: 'session-123',
        plan_id: 'plan-123'
      });

      expect(result).toEqual(mockBuild);
      expect(result.data.attributes.status).toBe('completed');
    });
  });

  describe('UI Utilities', () => {
    it('should display success message', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      
      ui.success('Operation completed successfully');
      
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('✅'));
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Operation completed successfully'));
      
      consoleSpy.mockRestore();
    });

    it('should display error message', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      ui.error('Operation failed');
      
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('❌'));
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Operation failed'));
      
      consoleSpy.mockRestore();
    });

    it('should display table', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      
      const data = [
        { Name: 'Template 1', Category: 'CRM', Version: '1.0.0' },
        { Name: 'Template 2', Category: 'LMS', Version: '1.0.0' }
      ];
      
      ui.table(data);
      
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Template 1'));
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Template 2'));
      
      consoleSpy.mockRestore();
    });
  });

  describe('Configuration', () => {
    it('should store and retrieve configuration', () => {
      const mockConfig = {
        get: jest.fn(),
        set: jest.fn()
      };

      (config as any) = mockConfig;

      mockConfig.get.mockReturnValue('test-token');
      expect(config.get('apiToken')).toBe('test-token');

      config.set('apiToken', 'new-token');
      expect(mockConfig.set).toHaveBeenCalledWith('apiToken', 'new-token');
    });
  });
});
