"""
SBH Meta-Builder Guided Prompt Composer UI
React component for scaffold generation interface.
"""

import React from 'react';
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Sparkles, FileText, Code, Settings, Play } from 'lucide-react';

interface ScaffoldComposerProps {
  onPlanGenerated?: (plan: any) => void;
  onBuildCompleted?: (result: any) => void;
}

interface Pattern {
  slug: string;
  name: string;
  description: string;
  tags: string[];
  inputs_schema: any;
}

interface Template {
  template_slug: string;
  template_version: string;
  merge_strategy: string;
  compose_points: string[];
}

export const ScaffoldComposer: React.FC<ScaffoldComposerProps> = ({
  onPlanGenerated,
  onBuildCompleted
}) => {
  const [mode, setMode] = useState<'guided' | 'freeform'>('guided');
  const [goalText, setGoalText] = useState('');
  const [guidedInput, setGuidedInput] = useState({
    role: '',
    context: '',
    task: '',
    audience: '',
    output: ''
  });
  const [selectedPatterns, setSelectedPatterns] = useState<string[]>([]);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isBuilding, setIsBuilding] = useState(false);
  const [currentPlan, setCurrentPlan] = useState<any>(null);
  const [planPreview, setPlanPreview] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPatternsAndTemplates();
  }, []);

  const loadPatternsAndTemplates = async () => {
    try {
      const [patternsRes, templatesRes] = await Promise.all([
        fetch('/api/meta/patterns'),
        fetch('/api/meta/templates')
      ]);

      if (patternsRes.ok) {
        const patternsData = await patternsRes.json();
        setPatterns(patternsData.data.map((p: any) => p.attributes));
      }

      if (templatesRes.ok) {
        const templatesData = await templatesRes.json();
        setTemplates(templatesData.data.map((t: any) => t.attributes));
      }
    } catch (err) {
      setError('Failed to load patterns and templates');
    }
  };

  const handlePlanGeneration = async () => {
    setIsPlanning(true);
    setError(null);

    try {
      const requestBody = {
        goal_text: goalText,
        mode: mode,
        guided_input: mode === 'guided' ? guidedInput : undefined,
        pattern_slugs: selectedPatterns,
        template_slugs: selectedTemplates,
        options: {
          llm: true,
          dry_run: false
        }
      };

      const response = await fetch('/api/meta/scaffold/plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.errors?.[0]?.detail || 'Plan generation failed');
      }

      const result = await response.json();
      const plan = result.data.attributes;
      
      setCurrentPlan(plan);
      setPlanPreview(generatePlanPreview(plan));
      
      if (onPlanGenerated) {
        onPlanGenerated(plan);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Plan generation failed');
    } finally {
      setIsPlanning(false);
    }
  };

  const handleBuild = async () => {
    if (!currentPlan) return;

    setIsBuilding(true);
    setError(null);

    try {
      const requestBody = {
        session_id: currentPlan.session_id,
        plan_id: currentPlan.id,
        export: {
          zip: true,
          github: {
            owner: 'sbh-user',
            repo: 'generated-app',
            branch: 'main'
          }
        },
        run_tests: true
      };

      const response = await fetch('/api/meta/scaffold/build', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.errors?.[0]?.detail || 'Build failed');
      }

      const result = await response.json();
      const buildResult = result.data.attributes;
      
      if (onBuildCompleted) {
        onBuildCompleted(buildResult);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Build failed');
    } finally {
      setIsBuilding(false);
    }
  };

  const generatePlanPreview = (plan: any) => {
    const planJson = plan.plan_json || {};
    
    return {
      entities: planJson.entities || [],
      apiEndpoints: planJson.api_endpoints || [],
      uiPages: planJson.ui_pages || [],
      features: {
        auth: planJson.auth || false,
        storage: planJson.storage || false,
        payments: planJson.payments || false,
        ai: planJson.ai_features || []
      },
      scorecard: plan.scorecard_json || {},
      risks: plan.risks || []
    };
  };

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex items-center space-x-2">
        <Sparkles className="h-6 w-6 text-blue-600" />
        <h1 className="text-2xl font-bold">SBH Meta-Builder</h1>
        <Badge variant="secondary">v1.0</Badge>
      </div>

      <Tabs defaultValue="composer" className="space-y-4">
        <TabsList>
          <TabsTrigger value="composer">Prompt Composer</TabsTrigger>
          <TabsTrigger value="preview">Plan Preview</TabsTrigger>
          <TabsTrigger value="inspector">Plan Inspector</TabsTrigger>
        </TabsList>

        <TabsContent value="composer" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Panel - Input */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="h-5 w-5" />
                    <span>Describe Your System</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Input Mode</label>
                    <Select value={mode} onValueChange={(value: 'guided' | 'freeform') => setMode(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="guided">Guided Form</SelectItem>
                        <SelectItem value="freeform">Freeform Text</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {mode === 'guided' ? (
                    <div className="space-y-4">
                      <div>
                        <label className="text-sm font-medium">Role</label>
                        <Input
                          placeholder="e.g., Developer, Product Manager, Startup Founder"
                          value={guidedInput.role}
                          onChange={(e) => setGuidedInput(prev => ({ ...prev, role: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Context</label>
                        <Textarea
                          placeholder="Describe your current situation, constraints, and goals..."
                          value={guidedInput.context}
                          onChange={(e) => setGuidedInput(prev => ({ ...prev, context: e.target.value }))}
                          rows={3}
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Task</label>
                        <Textarea
                          placeholder="What specific system or application do you want to build?"
                          value={guidedInput.task}
                          onChange={(e) => setGuidedInput(prev => ({ ...prev, task: e.target.value }))}
                          rows={3}
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Audience</label>
                        <Input
                          placeholder="e.g., Internal team, Customers, Partners"
                          value={guidedInput.audience}
                          onChange={(e) => setGuidedInput(prev => ({ ...prev, audience: e.target.value }))}
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium">Desired Output</label>
                        <Input
                          placeholder="e.g., Web app, API, Dashboard, Mobile app"
                          value={guidedInput.output}
                          onChange={(e) => setGuidedInput(prev => ({ ...prev, output: e.target.value }))}
                        />
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="text-sm font-medium">Goal Description</label>
                      <Textarea
                        placeholder="Describe your system idea in natural language..."
                        value={goalText}
                        onChange={(e) => setGoalText(e.target.value)}
                        rows={6}
                      />
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Code className="h-5 w-5" />
                    <span>Patterns & Templates</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium">Select Patterns</label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {patterns.map((pattern) => (
                        <div
                          key={pattern.slug}
                          className={`p-2 border rounded cursor-pointer ${
                            selectedPatterns.includes(pattern.slug)
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200'
                          }`}
                          onClick={() => {
                            setSelectedPatterns(prev =>
                              prev.includes(pattern.slug)
                                ? prev.filter(p => p !== pattern.slug)
                                : [...prev, pattern.slug]
                            );
                          }}
                        >
                          <div className="font-medium text-sm">{pattern.name}</div>
                          <div className="text-xs text-gray-600">{pattern.description}</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {pattern.tags.map((tag) => (
                              <Badge key={tag} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-sm font-medium">Select Templates</label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {templates.map((template) => (
                        <div
                          key={`${template.template_slug}-${template.template_version}`}
                          className={`p-2 border rounded cursor-pointer ${
                            selectedTemplates.includes(template.template_slug)
                              ? 'border-green-500 bg-green-50'
                              : 'border-gray-200'
                          }`}
                          onClick={() => {
                            setSelectedTemplates(prev =>
                              prev.includes(template.template_slug)
                                ? prev.filter(t => t !== template.template_slug)
                                : [...prev, template.template_slug]
                            );
                          }}
                        >
                          <div className="font-medium text-sm">{template.template_slug}</div>
                          <div className="text-xs text-gray-600">v{template.template_version}</div>
                          <div className="text-xs text-gray-500">{template.merge_strategy}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Panel - Preview & Actions */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Settings className="h-5 w-5" />
                    <span>Plan Preview</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {planPreview ? (
                    <div className="space-y-4">
                      <div>
                        <h4 className="font-medium mb-2">Entities</h4>
                        <div className="flex flex-wrap gap-2">
                          {planPreview.entities.map((entity: string) => (
                            <Badge key={entity} variant="secondary">
                              {entity}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h4 className="font-medium mb-2">API Endpoints</h4>
                        <div className="space-y-1">
                          {planPreview.apiEndpoints.slice(0, 5).map((endpoint: any, index: number) => (
                            <div key={index} className="text-sm font-mono bg-gray-100 p-1 rounded">
                              {endpoint.method} {endpoint.path}
                            </div>
                          ))}
                          {planPreview.apiEndpoints.length > 5 && (
                            <div className="text-sm text-gray-600">
                              +{planPreview.apiEndpoints.length - 5} more...
                            </div>
                          )}
                        </div>
                      </div>

                      <div>
                        <h4 className="font-medium mb-2">UI Pages</h4>
                        <div className="flex flex-wrap gap-2">
                          {planPreview.uiPages.map((page: string) => (
                            <Badge key={page} variant="outline">
                              {page}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div>
                        <h4 className="font-medium mb-2">Features</h4>
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(planPreview.features).map(([feature, enabled]) => (
                            <div key={feature} className="flex items-center space-x-2">
                              <div className={`w-2 h-2 rounded-full ${enabled ? 'bg-green-500' : 'bg-gray-300'}`} />
                              <span className="text-sm capitalize">{feature}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {planPreview.risks.length > 0 && (
                        <div>
                          <h4 className="font-medium mb-2 text-orange-600">Risks</h4>
                          <div className="space-y-1">
                            {planPreview.risks.map((risk: string, index: number) => (
                              <div key={index} className="text-sm text-orange-600">
                                • {risk}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center text-gray-500 py-8">
                      <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>Generate a plan to see the preview</p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Button
                    onClick={handlePlanGeneration}
                    disabled={isPlanning || (!goalText && mode === 'freeform')}
                    className="w-full"
                  >
                    {isPlanning ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating Plan...
                      </>
                    ) : (
                      <>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Generate Plan
                      </>
                    )}
                  </Button>

                  {currentPlan && (
                    <Button
                      onClick={handleBuild}
                      disabled={isBuilding}
                      variant="outline"
                      className="w-full"
                    >
                      {isBuilding ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Building...
                        </>
                      ) : (
                        <>
                          <Play className="mr-2 h-4 w-4" />
                          Build Scaffold
                        </>
                      )}
                    </Button>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="preview" className="space-y-6">
          {planPreview ? (
            <Card>
              <CardHeader>
                <CardTitle>Detailed Plan Preview</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-gray-100 p-4 rounded overflow-auto text-sm">
                  {JSON.stringify(planPreview, null, 2)}
                </pre>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <p className="text-gray-500">No plan generated yet</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="inspector" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Plan Inspector</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-500">Plan inspection features coming soon...</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
};

export default ScaffoldComposer;
