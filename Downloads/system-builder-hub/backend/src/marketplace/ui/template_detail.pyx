"""
SBH Marketplace Template Detail Page
Detailed view of a marketplace template with screenshots, features, and launch options.
"""

import React from 'react';
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
    Card, CardContent, CardHeader, CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
    ArrowLeft, Play, ExternalLink, Star, Users, Zap, Shield, 
    Globe, Sparkles, CheckCircle, AlertCircle, Info, Calendar,
    Settings, Loader2, Check, X
} from 'lucide-react';

interface Template {
    id: string;
    type: string;
    attributes: {
        slug: string;
        name: string;
        description: string;
        category: string;
        tags: string[];
        badges: string[];
        version: string;
        author: string;
        repository?: string;
        documentation?: string;
        screenshots: string[];
        demo_video_url?: string;
        features: string[];
        plans: Record<string, any>;
        guided_prompt_schema?: any;
        rbac_matrix?: Record<string, string[]>;
        api_endpoints?: Array<{method: string, path: string, description: string}>;
        ui_routes?: Array<{path: string, name: string, description: string}>;
        dependencies?: string[];
        conflicts?: string[];
        installation?: any;
        configuration?: any;
        examples?: Array<{name: string, description: string, config?: any}>;
        support?: any;
        changelog?: Array<{version: string, date: string, changes: string[]}>;
        is_active: boolean;
    };
}

export const TemplateDetail: React.FC = () => {
    const { slug } = useParams<{ slug: string }>();
    const navigate = useNavigate();
    const [template, setTemplate] = useState<Template | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedScreenshot, setSelectedScreenshot] = useState<number>(0);
    
    // Launch dialog
    const [launchDialogOpen, setLaunchDialogOpen] = useState(false);
    const [launchData, setLaunchData] = useState({
        tenant_name: '',
        domain: '',
        plan: 'starter',
        seed_demo_data: true
    });
    const [launching, setLaunching] = useState(false);

    useEffect(() => {
        if (slug) {
            loadTemplate(slug);
        }
    }, [slug]);

    const loadTemplate = async (templateSlug: string) => {
        try {
            setLoading(true);
            const response = await fetch(`/api/marketplace/templates/${templateSlug}`);
            
            if (!response.ok) {
                throw new Error('Template not found');
            }
            
            const data = await response.json();
            setTemplate(data.data);
            
            // Set default plan
            if (data.data.attributes.plans) {
                const planKeys = Object.keys(data.data.attributes.plans);
                if (planKeys.length > 0) {
                    setLaunchData(prev => ({ ...prev, plan: planKeys[0] }));
                }
            }
            
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load template');
        } finally {
            setLoading(false);
        }
    };

    const handleLaunchTemplate = async () => {
        if (!template || !launchData.tenant_name) return;

        try {
            setLaunching(true);
            const response = await fetch(`/api/marketplace/templates/${template.attributes.slug}/launch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(launchData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.errors?.[0]?.detail || 'Launch failed');
            }

            const result = await response.json();
            
            // Redirect to onboarding or show success message
            if (result.data.attributes.onboarding_url) {
                window.location.href = result.data.attributes.onboarding_url;
            } else {
                setLaunchDialogOpen(false);
                // Show success toast
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Launch failed');
        } finally {
            setLaunching(false);
        }
    };

    const getBadgeIcon = (badge: string) => {
        const iconMap: Record<string, React.ReactNode> = {
            'Multi-tenant': <Users className="w-4 h-4" />,
            'Stripe': <Zap className="w-4 h-4" />,
            'S3': <Globe className="w-4 h-4" />,
            'RBAC': <Shield className="w-4 h-4" />,
            'AI': <Sparkles className="w-4 h-4" />,
            'Automations': <Zap className="w-4 h-4" />,
            'Assessments': <CheckCircle className="w-4 h-4" />,
            'Scheduling': <Calendar className="w-4 h-4" />,
            'SLA': <AlertCircle className="w-4 h-4" />,
            'Portal': <ExternalLink className="w-4 h-4" />,
            'Real-time': <Zap className="w-4 h-4" />,
            'Customizable': <Settings className="w-4 h-4" />
        };
        return iconMap[badge] || <Info className="w-4 h-4" />;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
                    <p className="text-gray-600">Loading template...</p>
                </div>
            </div>
        );
    }

    if (error || !template) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <Alert variant="destructive">
                    <AlertDescription>{error || 'Template not found'}</AlertDescription>
                </Alert>
                <Button onClick={() => navigate('/ui/marketplace')} className="mt-4">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Marketplace
                </Button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-6xl mx-auto p-6">
                {/* Header */}
                <div className="mb-8">
                    <Button 
                        variant="ghost" 
                        onClick={() => navigate('/ui/marketplace')}
                        className="mb-4"
                    >
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Back to Marketplace
                    </Button>
                    
                    <div className="flex items-start justify-between">
                        <div className="flex-1">
                            <h1 className="text-3xl font-bold text-gray-900 mb-2">
                                {template.attributes.name}
                            </h1>
                            <p className="text-lg text-gray-600 mb-4">
                                {template.attributes.description}
                            </p>
                            <div className="flex items-center space-x-4 text-sm text-gray-500 mb-4">
                                <span>By {template.attributes.author}</span>
                                <span>v{template.attributes.version}</span>
                                <span>{template.attributes.category}</span>
                                <div className="flex items-center space-x-1">
                                    <Star className="w-4 h-4 text-yellow-400 fill-current" />
                                    <span>4.8</span>
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {template.attributes.badges.map(badge => (
                                    <Badge key={badge} variant="secondary" className="text-sm">
                                        {getBadgeIcon(badge)}
                                        <span className="ml-1">{badge}</span>
                                    </Badge>
                                ))}
                            </div>
                        </div>
                        <div className="flex space-x-2">
                            <Button
                                onClick={() => setLaunchDialogOpen(true)}
                                className="flex items-center space-x-2"
                            >
                                <Play className="w-4 h-4" />
                                <span>Launch Template</span>
                            </Button>
                            {template.attributes.documentation && (
                                <Button
                                    variant="outline"
                                    onClick={() => window.open(template.attributes.documentation, '_blank')}
                                >
                                    <ExternalLink className="w-4 h-4 mr-2" />
                                    Docs
                                </Button>
                            )}
                        </div>
                    </div>
                </div>

                {/* Main Content */}
                <Tabs defaultValue="overview" className="space-y-6">
                    <TabsList>
                        <TabsTrigger value="overview">Overview</TabsTrigger>
                        <TabsTrigger value="features">Features</TabsTrigger>
                        <TabsTrigger value="pricing">Pricing</TabsTrigger>
                        <TabsTrigger value="api">API</TabsTrigger>
                        <TabsTrigger value="changelog">Changelog</TabsTrigger>
                    </TabsList>

                    {/* Overview Tab */}
                    <TabsContent value="overview" className="space-y-6">
                        {/* Screenshots */}
                        {template.attributes.screenshots.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Screenshots</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-4">
                                        <div className="relative">
                                            <img
                                                src={template.attributes.screenshots[selectedScreenshot]}
                                                alt={`${template.attributes.name} screenshot`}
                                                className="w-full h-64 object-cover rounded-lg"
                                            />
                                        </div>
                                        {template.attributes.screenshots.length > 1 && (
                                            <div className="flex space-x-2 overflow-x-auto">
                                                {template.attributes.screenshots.map((screenshot, index) => (
                                                    <button
                                                        key={index}
                                                        onClick={() => setSelectedScreenshot(index)}
                                                        className={`flex-shrink-0 w-20 h-20 rounded border-2 ${
                                                            index === selectedScreenshot 
                                                                ? 'border-blue-500' 
                                                                : 'border-gray-200'
                                                        }`}
                                                    >
                                                        <img
                                                            src={screenshot}
                                                            alt={`Screenshot ${index + 1}`}
                                                            className="w-full h-full object-cover rounded"
                                                        />
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* Demo Video */}
                        {template.attributes.demo_video_url && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Demo Video</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="aspect-video bg-gray-100 rounded-lg flex items-center justify-center">
                                        <Button
                                            onClick={() => window.open(template.attributes.demo_video_url, '_blank')}
                                            variant="outline"
                                        >
                                            <Play className="w-4 h-4 mr-2" />
                                            Watch Demo
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* Quick Start */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Quick Start</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    {template.attributes.installation?.steps?.map((step: string, index: number) => (
                                        <div key={index} className="flex items-start space-x-3">
                                            <div className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">
                                                {index + 1}
                                            </div>
                                            <p className="text-gray-700">{step}</p>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* Features Tab */}
                    <TabsContent value="features" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Features</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {template.attributes.features.map((feature, index) => (
                                        <div key={index} className="flex items-center space-x-2">
                                            <Check className="w-4 h-4 text-green-500" />
                                            <span>{feature}</span>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        {/* UI Routes */}
                        {template.attributes.ui_routes && template.attributes.ui_routes.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>UI Pages</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        {template.attributes.ui_routes.map((route, index) => (
                                            <div key={index} className="flex items-center justify-between p-3 border rounded">
                                                <div>
                                                    <h4 className="font-medium">{route.name}</h4>
                                                    <p className="text-sm text-gray-600">{route.description}</p>
                                                </div>
                                                <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                                                    {route.path}
                                                </code>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    {/* Pricing Tab */}
                    <TabsContent value="pricing" className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {Object.entries(template.attributes.plans).map(([key, plan]) => (
                                <Card key={key} className="relative">
                                    {key === 'pro' && (
                                        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                                            <Badge className="bg-blue-500 text-white">Most Popular</Badge>
                                        </div>
                                    )}
                                    <CardHeader>
                                        <CardTitle className="text-center">{plan.name}</CardTitle>
                                        <div className="text-center">
                                            <span className="text-3xl font-bold">${plan.price}</span>
                                            <span className="text-gray-600">/month</span>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <ul className="space-y-2">
                                            {plan.features.map((feature: string, index: number) => (
                                                <li key={index} className="flex items-center space-x-2">
                                                    <Check className="w-4 h-4 text-green-500" />
                                                    <span className="text-sm">{feature}</span>
                                                </li>
                                            ))}
                                        </ul>
                                        <Button 
                                            className="w-full mt-4"
                                            variant={key === 'pro' ? 'default' : 'outline'}
                                            onClick={() => {
                                                setLaunchData(prev => ({ ...prev, plan: key }));
                                                setLaunchDialogOpen(true);
                                            }}
                                        >
                                            Select {plan.name}
                                        </Button>
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </TabsContent>

                    {/* API Tab */}
                    <TabsContent value="api" className="space-y-6">
                        {template.attributes.api_endpoints && template.attributes.api_endpoints.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>API Endpoints</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        {template.attributes.api_endpoints.map((endpoint, index) => (
                                            <div key={index} className="flex items-center justify-between p-3 border rounded">
                                                <div className="flex items-center space-x-3">
                                                    <Badge variant={endpoint.method === 'GET' ? 'default' : 'secondary'}>
                                                        {endpoint.method}
                                                    </Badge>
                                                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                                                        {endpoint.path}
                                                    </code>
                                                </div>
                                                <span className="text-sm text-gray-600">{endpoint.description}</span>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    {/* Changelog Tab */}
                    <TabsContent value="changelog" className="space-y-6">
                        {template.attributes.changelog && template.attributes.changelog.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle>Changelog</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-4">
                                        {template.attributes.changelog.map((release, index) => (
                                            <div key={index} className="border-l-2 border-gray-200 pl-4">
                                                <div className="flex items-center space-x-2 mb-2">
                                                    <Badge variant="outline">v{release.version}</Badge>
                                                    <span className="text-sm text-gray-500">{release.date}</span>
                                                </div>
                                                <ul className="space-y-1">
                                                    {release.changes.map((change, changeIndex) => (
                                                        <li key={changeIndex} className="text-sm text-gray-700">
                                                            • {change}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>
                </Tabs>

                {/* Launch Dialog */}
                <Dialog open={launchDialogOpen} onOpenChange={setLaunchDialogOpen}>
                    <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle>Launch {template.attributes.name}</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Tenant Name</label>
                                <input
                                    type="text"
                                    placeholder="Enter tenant name"
                                    value={launchData.tenant_name}
                                    onChange={(e) => setLaunchData(prev => ({ ...prev, tenant_name: e.target.value }))}
                                    className="w-full p-2 border rounded"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Domain (Optional)</label>
                                <input
                                    type="text"
                                    placeholder="your-domain.com"
                                    value={launchData.domain}
                                    onChange={(e) => setLaunchData(prev => ({ ...prev, domain: e.target.value }))}
                                    className="w-full p-2 border rounded"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Plan</label>
                                <select
                                    value={launchData.plan}
                                    onChange={(e) => setLaunchData(prev => ({ ...prev, plan: e.target.value }))}
                                    className="w-full p-2 border rounded"
                                >
                                    {Object.entries(template.attributes.plans).map(([key, plan]) => (
                                        <option key={key} value={key}>
                                            {plan.name} - ${plan.price}/month
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex items-center space-x-2">
                                <input
                                    type="checkbox"
                                    id="seed-demo"
                                    checked={launchData.seed_demo_data}
                                    onChange={(e) => setLaunchData(prev => ({ ...prev, seed_demo_data: e.target.checked }))}
                                    className="rounded"
                                />
                                <label htmlFor="seed-demo" className="text-sm">
                                    Seed demo data
                                </label>
                            </div>
                            <div className="flex space-x-2">
                                <Button
                                    onClick={handleLaunchTemplate}
                                    disabled={launching || !launchData.tenant_name}
                                    className="flex-1"
                                >
                                    {launching ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                            Launching...
                                        </>
                                    ) : (
                                        <>
                                            <Play className="w-4 h-4 mr-2" />
                                            Launch Template
                                        </>
                                    )}
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={() => setLaunchDialogOpen(false)}
                                    disabled={launching}
                                >
                                    Cancel
                                </Button>
                            </div>
                        </div>
                    </DialogContent>
                </Dialog>

                {error && (
                    <Alert variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}
            </div>
        </div>
    );
};

export default TemplateDetail;
