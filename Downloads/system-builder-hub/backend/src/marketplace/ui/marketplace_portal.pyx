"""
SBH Marketplace & Builder Portal UI
Main React component for the marketplace and builder portal.
"""

import React from 'react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Card, CardContent, CardHeader, CardTitle 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
    Search, Filter, Grid, List, Play, Sparkles, History, 
    ExternalLink, Star, Users, Zap, Shield, Globe,
    Loader2, CheckCircle, AlertCircle, Info
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
        screenshots: string[];
        demo_video_url?: string;
        documentation?: string;
        features: string[];
        plans: Record<string, any>;
        is_active: boolean;
    };
}

interface ScaffoldHistory {
    id: string;
    name: string;
    status: 'building' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
}

export const MarketplacePortal: React.FC = () => {
    const [activeTab, setActiveTab] = useState('marketplace');
    const [templates, setTemplates] = useState<Template[]>([]);
    const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);
    const [categories, setCategories] = useState<string[]>([]);
    const [tags, setTags] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    
    // Filters
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState<string>('');
    const [selectedTags, setSelectedTags] = useState<string[]>([]);
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    
    // Launch dialog
    const [launchDialogOpen, setLaunchDialogOpen] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
    const [launchData, setLaunchData] = useState({
        tenant_name: '',
        domain: '',
        plan: 'starter',
        seed_demo_data: true
    });
    const [launching, setLaunching] = useState(false);
    
    // Scaffold history
    const [scaffoldHistory, setScaffoldHistory] = useState<ScaffoldHistory[]>([]);

    useEffect(() => {
        loadTemplates();
        loadScaffoldHistory();
    }, []);

    useEffect(() => {
        filterTemplates();
    }, [templates, searchQuery, selectedCategory, selectedTags]);

    const loadTemplates = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/marketplace/templates');
            
            if (!response.ok) {
                throw new Error('Failed to load templates');
            }
            
            const data = await response.json();
            setTemplates(data.data);
            
            // Extract categories and tags
            const allCategories = new Set<string>();
            const allTags = new Set<string>();
            
            data.data.forEach((template: Template) => {
                if (template.attributes.category) {
                    allCategories.add(template.attributes.category);
                }
                template.attributes.tags.forEach(tag => allTags.add(tag));
            });
            
            setCategories(Array.from(allCategories));
            setTags(Array.from(allTags));
            
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load templates');
        } finally {
            setLoading(false);
        }
    };

    const loadScaffoldHistory = async () => {
        try {
            const response = await fetch('/api/meta/scaffold/history');
            if (response.ok) {
                const data = await response.json();
                setScaffoldHistory(data.data || []);
            }
        } catch (err) {
            console.error('Failed to load scaffold history:', err);
        }
    };

    const filterTemplates = () => {
        let filtered = templates;

        // Search filter
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            filtered = filtered.filter(template =>
                template.attributes.name.toLowerCase().includes(query) ||
                template.attributes.description.toLowerCase().includes(query) ||
                template.attributes.tags.some(tag => tag.toLowerCase().includes(query))
            );
        }

        // Category filter
        if (selectedCategory) {
            filtered = filtered.filter(template =>
                template.attributes.category === selectedCategory
            );
        }

        // Tags filter
        if (selectedTags.length > 0) {
            filtered = filtered.filter(template =>
                selectedTags.every(tag => template.attributes.tags.includes(tag))
            );
        }

        setFilteredTemplates(filtered);
    };

    const handleLaunchTemplate = async () => {
        if (!selectedTemplate || !launchData.tenant_name) return;

        try {
            setLaunching(true);
            const response = await fetch(`/api/marketplace/templates/${selectedTemplate.attributes.slug}/launch`, {
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
            'Multi-tenant': <Users className="w-3 h-3" />,
            'Stripe': <Zap className="w-3 h-3" />,
            'S3': <Globe className="w-3 h-3" />,
            'RBAC': <Shield className="w-3 h-3" />,
            'AI': <Sparkles className="w-3 h-3" />,
            'Automations': <Zap className="w-3 h-3" />,
            'Assessments': <CheckCircle className="w-3 h-3" />,
            'Scheduling': <Calendar className="w-3 h-3" />,
            'SLA': <AlertCircle className="w-3 h-3" />,
            'Portal': <ExternalLink className="w-3 h-3" />,
            'Real-time': <Zap className="w-3 h-3" />,
            'Customizable': <Settings className="w-3 h-3" />
        };
        return iconMap[badge] || <Info className="w-3 h-3" />;
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircle className="w-4 h-4 text-green-500" />;
            case 'building':
                return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
            case 'failed':
                return <AlertCircle className="w-4 h-4 text-red-500" />;
            default:
                return <Info className="w-4 h-4 text-gray-500" />;
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
                    <p className="text-gray-600">Loading marketplace...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto p-6">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">
                        SBH Marketplace & Builder Portal
                    </h1>
                    <p className="text-gray-600">
                        Browse ready-to-use templates or build custom systems with AI
                    </p>
                </div>

                {/* Main Tabs */}
                <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
                    <TabsList className="grid w-full grid-cols-3">
                        <TabsTrigger value="marketplace" className="flex items-center space-x-2">
                            <Grid className="w-4 h-4" />
                            <span>Marketplace</span>
                        </TabsTrigger>
                        <TabsTrigger value="builder" className="flex items-center space-x-2">
                            <Sparkles className="w-4 h-4" />
                            <span>Builder Portal</span>
                        </TabsTrigger>
                        <TabsTrigger value="history" className="flex items-center space-x-2">
                            <History className="w-4 h-4" />
                            <span>History</span>
                        </TabsTrigger>
                    </TabsList>

                    {/* Marketplace Tab */}
                    <TabsContent value="marketplace" className="space-y-6">
                        {/* Filters */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center space-x-2">
                                    <Filter className="w-5 h-5" />
                                    <span>Filters</span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    {/* Search */}
                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                                        <Input
                                            placeholder="Search templates..."
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            className="pl-10"
                                        />
                                    </div>

                                    {/* Category Filter */}
                                    <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="All Categories" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="">All Categories</SelectItem>
                                            {categories.map(category => (
                                                <SelectItem key={category} value={category}>
                                                    {category}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>

                                    {/* Tags Filter */}
                                    <Select 
                                        value={selectedTags.join(',')} 
                                        onValueChange={(value) => setSelectedTags(value ? value.split(',') : [])}
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="All Tags" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="">All Tags</SelectItem>
                                            {tags.map(tag => (
                                                <SelectItem key={tag} value={tag}>
                                                    {tag}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>

                                    {/* View Mode */}
                                    <div className="flex space-x-2">
                                        <Button
                                            variant={viewMode === 'grid' ? 'default' : 'outline'}
                                            size="sm"
                                            onClick={() => setViewMode('grid')}
                                        >
                                            <Grid className="w-4 h-4" />
                                        </Button>
                                        <Button
                                            variant={viewMode === 'list' ? 'default' : 'outline'}
                                            size="sm"
                                            onClick={() => setViewMode('list')}
                                        >
                                            <List className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Templates Grid/List */}
                        <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-4'}>
                            <AnimatePresence>
                                {filteredTemplates.map((template, index) => (
                                    <motion.div
                                        key={template.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: -20 }}
                                        transition={{ delay: index * 0.1 }}
                                    >
                                        <Card className="h-full hover:shadow-lg transition-shadow">
                                            <CardHeader>
                                                <div className="flex items-start justify-between">
                                                    <div className="flex-1">
                                                        <CardTitle className="text-lg mb-2">
                                                            {template.attributes.name}
                                                        </CardTitle>
                                                        <p className="text-sm text-gray-600 mb-3">
                                                            {template.attributes.description}
                                                        </p>
                                                        <div className="flex flex-wrap gap-1 mb-3">
                                                            {template.attributes.badges.map(badge => (
                                                                <Badge key={badge} variant="secondary" className="text-xs">
                                                                    {getBadgeIcon(badge)}
                                                                    <span className="ml-1">{badge}</span>
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    {template.attributes.screenshots.length > 0 && (
                                                        <img
                                                            src={template.attributes.screenshots[0]}
                                                            alt={template.attributes.name}
                                                            className="w-16 h-16 object-cover rounded"
                                                        />
                                                    )}
                                                </div>
                                            </CardHeader>
                                            <CardContent>
                                                <div className="space-y-3">
                                                    <div className="flex items-center justify-between text-sm text-gray-500">
                                                        <span>By {template.attributes.author}</span>
                                                        <span>v{template.attributes.version}</span>
                                                    </div>
                                                    
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex space-x-2">
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                onClick={() => {
                                                                    setSelectedTemplate(template);
                                                                    setLaunchDialogOpen(true);
                                                                }}
                                                            >
                                                                <Play className="w-4 h-4 mr-1" />
                                                                Launch
                                                            </Button>
                                                            {template.attributes.documentation && (
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => window.open(template.attributes.documentation, '_blank')}
                                                                >
                                                                    <ExternalLink className="w-4 h-4 mr-1" />
                                                                    Docs
                                                                </Button>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center space-x-1">
                                                            <Star className="w-4 h-4 text-yellow-400 fill-current" />
                                                            <span className="text-sm text-gray-600">4.8</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </div>

                        {filteredTemplates.length === 0 && !loading && (
                            <Card>
                                <CardContent className="text-center py-12">
                                    <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                                    <h3 className="text-lg font-medium text-gray-900 mb-2">No templates found</h3>
                                    <p className="text-gray-600">Try adjusting your search or filters</p>
                                </CardContent>
                            </Card>
                        )}
                    </TabsContent>

                    {/* Builder Portal Tab */}
                    <TabsContent value="builder" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center space-x-2">
                                    <Sparkles className="w-5 h-5" />
                                    <span>AI-Powered System Builder</span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-gray-600 mb-6">
                                    Describe your system idea in natural language and let AI generate a complete scaffold for you.
                                </p>
                                <Button 
                                    onClick={() => window.location.href = '/ui/meta/scaffold'}
                                    className="w-full"
                                >
                                    <Sparkles className="w-4 h-4 mr-2" />
                                    Start Building
                                </Button>
                            </CardContent>
                        </Card>
                    </TabsContent>

                    {/* History Tab */}
                    <TabsContent value="history" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center space-x-2">
                                    <History className="w-5 h-5" />
                                    <span>Scaffold History</span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                {scaffoldHistory.length === 0 ? (
                                    <div className="text-center py-8">
                                        <History className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                                        <h3 className="text-lg font-medium text-gray-900 mb-2">No scaffolds yet</h3>
                                        <p className="text-gray-600">Start building your first system</p>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        {scaffoldHistory.map((scaffold) => (
                                            <div key={scaffold.id} className="flex items-center justify-between p-4 border rounded-lg">
                                                <div className="flex items-center space-x-3">
                                                    {getStatusIcon(scaffold.status)}
                                                    <div>
                                                        <h4 className="font-medium">{scaffold.name}</h4>
                                                        <p className="text-sm text-gray-500">
                                                            Created {new Date(scaffold.created_at).toLocaleDateString()}
                                                        </p>
                                                    </div>
                                                </div>
                                                <Badge variant={scaffold.status === 'completed' ? 'default' : scaffold.status === 'building' ? 'secondary' : 'destructive'}>
                                                    {scaffold.status}
                                                </Badge>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>

                {/* Launch Dialog */}
                <Dialog open={launchDialogOpen} onOpenChange={setLaunchDialogOpen}>
                    <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle>Launch {selectedTemplate?.attributes.name}</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Tenant Name</label>
                                <Input
                                    placeholder="Enter tenant name"
                                    value={launchData.tenant_name}
                                    onChange={(e) => setLaunchData(prev => ({ ...prev, tenant_name: e.target.value }))}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Domain (Optional)</label>
                                <Input
                                    placeholder="your-domain.com"
                                    value={launchData.domain}
                                    onChange={(e) => setLaunchData(prev => ({ ...prev, domain: e.target.value }))}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2">Plan</label>
                                <Select value={launchData.plan} onValueChange={(value) => setLaunchData(prev => ({ ...prev, plan: value }))}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {selectedTemplate && Object.entries(selectedTemplate.attributes.plans).map(([key, plan]) => (
                                            <SelectItem key={key} value={key}>
                                                {plan.name} - ${plan.price}/month
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
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

export default MarketplacePortal;
