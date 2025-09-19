'use client';

import React, { useState } from 'react';
import { 
  Globe, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  ExternalLink, 
  Copy, 
  Info,
  Shield,
  Zap,
  Settings
} from 'lucide-react';

interface DomainConfig {
  domain: string;
  type: 'custom' | 'sbh_managed';
  status: 'idle' | 'validating' | 'valid' | 'invalid' | 'deploying' | 'deployed' | 'error';
  validation?: {
    is_valid: boolean;
    domain_type: string;
    setup_instructions?: string;
    dns_records?: Array<{
      type: string;
      name: string;
      value: string;
      ttl: number;
    }>;
    ssl_status?: 'pending' | 'issued' | 'failed';
    deployment_url?: string;
  };
  error?: string;
}

interface DomainManagementProps {
  systemId: string;
  onDomainConfigured: (config: DomainConfig) => void;
}

export default function DomainManagement({ systemId, onDomainConfigured }: DomainManagementProps) {
  const [domain, setDomain] = useState('');
  const [domainType, setDomainType] = useState<'custom' | 'sbh_managed'>('sbh_managed');
  const [config, setConfig] = useState<DomainConfig | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);

  const validateDomain = async (domainToValidate: string) => {
    if (!domainToValidate.trim()) return;

    setIsValidating(true);
    setConfig(prev => prev ? { ...prev, status: 'validating' } : null);

    try {
      const response = await fetch('/api/system/domain/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: domainToValidate })
      });

      const data = await response.json();
      
      if (data.success) {
        const newConfig: DomainConfig = {
          domain: domainToValidate,
          type: data.domain_type === 'custom' ? 'custom' : 'sbh_managed',
          status: data.is_valid ? 'valid' : 'invalid',
          validation: data
        };
        
        setConfig(newConfig);
        onDomainConfigured(newConfig);
      } else {
        setConfig(prev => prev ? { ...prev, status: 'error', error: data.error } : null);
      }
    } catch (error) {
      setConfig(prev => prev ? { ...prev, status: 'error', error: 'Validation failed' } : null);
    } finally {
      setIsValidating(false);
    }
  };

  const deployWithDomain = async () => {
    if (!config || !systemId) return;

    setIsDeploying(true);
    setConfig(prev => prev ? { ...prev, status: 'deploying' } : null);

    try {
      const response = await fetch(`/api/system/deploy/${systemId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: config.domain,
          domain_type: config.type
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setConfig(prev => prev ? { 
          ...prev, 
          status: 'deployed',
          validation: { ...prev.validation, deployment_url: data.deployment_url }
        } : null);
      } else {
        setConfig(prev => prev ? { ...prev, status: 'error', error: data.error } : null);
      }
    } catch (error) {
      setConfig(prev => prev ? { ...prev, status: 'error', error: 'Deployment failed' } : null);
    } finally {
      setIsDeploying(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const generateSBHDomain = () => {
    const systemName = systemId.split('-')[0] || 'system';
    const sbhDomain = `${systemName}.sbh.umbervale.com`;
    setDomain(sbhDomain);
    setDomainType('sbh_managed');
    validateDomain(sbhDomain);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'valid':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'invalid':
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'validating':
      case 'deploying':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'deployed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      default:
        return <Globe className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'validating':
        return 'Validating domain...';
      case 'valid':
        return 'Domain is valid';
      case 'invalid':
        return 'Domain is invalid';
      case 'deploying':
        return 'Deploying...';
      case 'deployed':
        return 'Deployed successfully';
      case 'error':
        return 'Error occurred';
      default:
        return 'Ready to validate';
    }
  };

  return (
    <div className="space-y-6">
      {/* Domain Input */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Domain Configuration</h3>
        
        <div className="space-y-4">
          {/* Domain Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Domain Type</label>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setDomainType('sbh_managed')}
                className={`p-4 border-2 rounded-lg text-left transition-colors ${
                  domainType === 'sbh_managed'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Zap className="h-5 w-5 text-blue-500" />
                  <div>
                    <div className="font-medium">SBH Managed</div>
                    <div className="text-sm text-gray-600">Quick deployment with SBH subdomain</div>
                  </div>
                </div>
              </button>
              
              <button
                onClick={() => setDomainType('custom')}
                className={`p-4 border-2 rounded-lg text-left transition-colors ${
                  domainType === 'custom'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Globe className="h-5 w-5 text-green-500" />
                  <div>
                    <div className="font-medium">Custom Domain</div>
                    <div className="text-sm text-gray-600">Use your own domain</div>
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Domain Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Domain</label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder={domainType === 'sbh_managed' ? 'system-name.sbh.umbervale.com' : 'yourdomain.com'}
                className="flex-1 p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {domainType === 'sbh_managed' && (
                <button
                  onClick={generateSBHDomain}
                  className="px-4 py-3 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200"
                >
                  Generate
                </button>
              )}
            </div>
          </div>

          {/* Validate Button */}
          <button
            onClick={() => validateDomain(domain)}
            disabled={!domain.trim() || isValidating}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {isValidating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Globe className="h-4 w-4" />
            )}
            <span>Validate Domain</span>
          </button>
        </div>
      </div>

      {/* Domain Status */}
      {config && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Domain Status</h3>
            <div className="flex items-center space-x-2">
              {getStatusIcon(config.status)}
              <span className="text-sm font-medium text-gray-700">
                {getStatusText(config.status)}
              </span>
            </div>
          </div>

          {config.error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <span className="text-red-800">{config.error}</span>
              </div>
            </div>
          )}

          {config.validation && (
            <div className="space-y-4">
              {/* Domain Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Domain</label>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-sm text-gray-900">{config.domain}</span>
                    <button
                      onClick={() => copyToClipboard(config.domain)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Type</label>
                  <span className="text-sm text-gray-900 capitalize">{config.validation.domain_type}</span>
                </div>
              </div>

              {/* SSL Status */}
              {config.validation.ssl_status && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">SSL Certificate</label>
                  <div className="flex items-center space-x-2 mt-1">
                    {config.validation.ssl_status === 'issued' ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : config.validation.ssl_status === 'pending' ? (
                      <Loader2 className="h-4 w-4 text-yellow-500 animate-spin" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="text-sm text-gray-900 capitalize">
                      {config.validation.ssl_status}
                    </span>
                  </div>
                </div>
              )}

              {/* DNS Records */}
              {config.validation.dns_records && config.validation.dns_records.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">DNS Records</label>
                  <div className="space-y-2">
                    {config.validation.dns_records.map((record, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
                        <div className="flex items-center space-x-4">
                          <span className="text-sm font-medium text-gray-900">{record.type}</span>
                          <span className="text-sm text-gray-700">{record.name}</span>
                          <span className="text-sm text-gray-700">{record.value}</span>
                        </div>
                        <button
                          onClick={() => copyToClipboard(record.value)}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Setup Instructions */}
              {config.validation.setup_instructions && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Setup Instructions</label>
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
                    <div className="flex items-start space-x-2">
                      <Info className="h-4 w-4 text-blue-600 mt-0.5" />
                      <div className="text-sm text-blue-800 whitespace-pre-line">
                        {config.validation.setup_instructions}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Deployment URL */}
              {config.validation.deployment_url && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Deployment URL</label>
                  <div className="flex items-center space-x-2">
                    <a
                      href={config.validation.deployment_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center space-x-2 text-blue-600 hover:text-blue-700"
                    >
                      <span className="text-sm">{config.validation.deployment_url}</span>
                      <ExternalLink className="h-4 w-4" />
                    </a>
                    <button
                      onClick={() => copyToClipboard(config.validation.deployment_url!)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Deploy Button */}
          {config.status === 'valid' && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <button
                onClick={deployWithDomain}
                disabled={isDeploying}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {isDeploying ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Shield className="h-4 w-4" />
                )}
                <span>Deploy to {config.domain}</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* Domain Management Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <div className="flex items-start space-x-3">
          <Settings className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-blue-900">Domain Management</h4>
            <div className="mt-2 text-sm text-blue-800 space-y-1">
              <p>• <strong>SBH Managed:</strong> Automatic DNS and SSL setup with SBH subdomains</p>
              <p>• <strong>Custom Domain:</strong> You'll need to configure DNS records in your domain provider</p>
              <p>• <strong>SSL Certificates:</strong> Automatically provisioned via AWS Certificate Manager</p>
              <p>• <strong>Global CDN:</strong> Your app will be served via CloudFront for optimal performance</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
