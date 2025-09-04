import axios, { AxiosInstance, AxiosResponse } from 'axios';
import config from './config';
import chalk from 'chalk';

export class SBHAPI {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.get('apiUrl'),
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token if available
    const token = config.get('apiToken');
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          console.error(chalk.red('Authentication failed. Please run "sbh login" to authenticate.'));
        } else if (error.response?.status === 403) {
          console.error(chalk.red('Access denied. Check your permissions.'));
        } else if (error.response?.status >= 500) {
          console.error(chalk.red('Server error. Please try again later.'));
        }
        throw error;
      }
    );
  }

  async get<T>(url: string, params?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.get(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.post(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response: AxiosResponse<T> = await this.client.put(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response: AxiosResponse<T> = await this.client.delete(url);
    return response.data;
  }

  // Marketplace API methods
  async listTemplates(params?: any) {
    return this.get('/api/marketplace/templates', params);
  }

  async getTemplate(slug: string) {
    return this.get(`/api/marketplace/templates/${slug}`);
  }

  async launchTemplate(slug: string, data: any) {
    return this.post(`/api/marketplace/templates/${slug}/launch`, data);
  }

  async listCategories() {
    return this.get('/api/marketplace/categories');
  }

  // Meta-Builder API methods
  async createScaffoldPlan(data: any) {
    return this.post('/api/meta/scaffold/plan', data);
  }

  async buildScaffold(data: any) {
    return this.post('/api/meta/scaffold/build', data);
  }

  async getScaffoldHistory() {
    return this.get('/api/meta/scaffold/history');
  }

  async runEvaluation(data: any) {
    return this.post('/api/meta/eval/run', data);
  }

  // Auth methods
  async login(credentials: { email: string; password: string }) {
    return this.post('/api/auth/login', credentials);
  }

  async getProfile() {
    return this.get('/api/auth/profile');
  }
}

export default new SBHAPI();
