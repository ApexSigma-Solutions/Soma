import { useState } from 'react';
import { useSettingsStore, Setting } from '@/lib/store/useSettingsStore';
import { useSystemStore } from '@/lib/store/systemStore';
import { useAnalyticsStore } from '@/lib/store/useAnalyticsStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

// Simple Label component
const Label = ({ htmlFor, children, className = '' }: { htmlFor?: string; children: React.ReactNode; className?: string }) => (
  <label htmlFor={htmlFor} className={`text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 ${className}`}>
    {children}
  </label>
);
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, Save, RotateCcw, Sun, Moon, Palette } from 'lucide-react';

export function SettingsPage() {
  const { settings, updateSetting, resetSettings } = useSettingsStore();
  const { theme, toggleTheme } = useSystemStore();
  const { resetMetrics, totalCaptures, totalIngestions, totalSearches } = useAnalyticsStore();
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const handleSave = () => {
    setSaveMessage('Settings saved successfully');
    setTimeout(() => setSaveMessage(null), 3000);
  };

  const handleReset = () => {
    if (confirm('Reset all settings to defaults? This cannot be undone.')) {
      resetSettings();
      setSaveMessage('Settings reset to defaults');
      setTimeout(() => setSaveMessage(null), 3000);
    }
  };

  const renderSetting = (setting: Setting) => {
    switch (setting.type) {
      case 'text':
        return (
          <div key={setting.key} className="space-y-2">
            <Label htmlFor={setting.key}>{setting.label}</Label>
            <Input
              id={setting.key}
              type="text"
              value={setting.value as string}
              onChange={(e) => updateSetting(setting.key, e.target.value)}
              placeholder={setting.description}
              className="bg-card border-border"
            />
            {setting.description && (
              <p className="text-sm text-muted-foreground">{setting.description}</p>
            )}
          </div>
        );

      case 'number':
        return (
          <div key={setting.key} className="space-y-2">
            <Label htmlFor={setting.key}>{setting.label}</Label>
            <Input
              id={setting.key}
              type="number"
              value={setting.value as number}
              onChange={(e) => updateSetting(setting.key, parseFloat(e.target.value))}
              step={setting.key === 'ui_pattern_opacity' ? '0.01' : '1'}
              min={setting.key === 'ui_pattern_opacity' ? '0' : undefined}
              max={setting.key === 'ui_pattern_opacity' ? '1' : undefined}
              className="bg-card border-border"
            />
            {setting.description && (
              <p className="text-sm text-muted-foreground">{setting.description}</p>
            )}
          </div>
        );

      case 'boolean':
        return (
          <div key={setting.key} className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor={setting.key}>{setting.label}</Label>
              {setting.description && (
                <p className="text-sm text-muted-foreground">{setting.description}</p>
              )}
            </div>
            <input
              id={setting.key}
              type="checkbox"
              checked={setting.value as boolean}
              onChange={(e) => updateSetting(setting.key, e.target.checked)}
              className="h-4 w-4"
            />
          </div>
        );

      case 'select':
        return (
          <div key={setting.key} className="space-y-2">
            <Label htmlFor={setting.key}>{setting.label}</Label>
            <select
              id={setting.key}
              value={setting.value as string}
              onChange={(e) => updateSetting(setting.key, e.target.value)}
              className="w-full px-3 py-2 bg-card border border-border rounded-md"
            >
              {setting.options?.map((option) => (
                <option key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </option>
              ))}
            </select>
            {setting.description && (
              <p className="text-sm text-muted-foreground">{setting.description}</p>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  const sections = {
    general: settings.filter(s => s.section === 'general'),
    appearance: settings.filter(s => s.section === 'appearance'),
    integrations: settings.filter(s => s.section === 'integrations'),
    advanced: settings.filter(s => s.section === 'advanced')
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-heading font-bold text-teal-400 mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Configure your CortexBridge preferences and integrations
        </p>
      </div>

      {saveMessage && (
        <div className="bg-teal-500/10 border border-teal-500/30 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-teal-400 mt-0.5" />
          <span className="text-teal-400">{saveMessage}</span>
        </div>
      )}

      <Tabs defaultValue="general" className="space-y-6">
        <TabsList className="bg-card border border-border">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
          <TabsTrigger value="system">System</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-4">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
              <CardDescription>Basic project configuration</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {sections.general.map(renderSetting)}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appearance" className="space-y-4">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5" /> Appearance Settings
              </CardTitle>
              <CardDescription>Customize the look and feel</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Theme Toggle (from existing systemStore) */}
              <div className="flex items-center justify-between pb-4 border-b border-border">
                <div>
                  <h4 className="font-medium">Theme</h4>
                  <p className="text-sm text-muted-foreground">
                    Current: {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
                  </p>
                </div>
                <Button onClick={toggleTheme} variant="outline" className="gap-2">
                  {theme === 'dark' ? (
                    <>
                      <Sun className="h-4 w-4" /> Switch to Light
                    </>
                  ) : (
                    <>
                      <Moon className="h-4 w-4" /> Switch to Dark
                    </>
                  )}
                </Button>
              </div>
              
              {/* Pattern Settings */}
              {sections.appearance.map(renderSetting)}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="integrations" className="space-y-4">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Integration Settings</CardTitle>
              <CardDescription>Connect external services</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {sections.integrations.map(renderSetting)}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-4">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Advanced Settings</CardTitle>
              <CardDescription>Debug and performance options</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {sections.advanced.map(renderSetting)}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system" className="space-y-4">
          {/* Data & Privacy */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Data & Privacy</CardTitle>
              <CardDescription>Manage your stored analytics and activity data</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Analytics</h4>
                  <p className="text-sm text-muted-foreground">
                    {totalCaptures} captures · {totalIngestions} ingestions · {totalSearches} searches
                  </p>
                </div>
                <Button onClick={resetMetrics} variant="destructive" className="gap-2">
                  <RotateCcw className="h-4 w-4" /> Reset Metrics
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* About */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>About</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p><strong>CortexBridge</strong> v1.0.0</p>
                <p>The Executive Control Plane for the ApexSigma Omega Ecosystem.</p>
                <p>© 2026 ApexSigma Solutions</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex gap-4">
        <Button onClick={handleSave} className="bg-teal-500 text-background hover:bg-teal-600">
          <Save className="h-4 w-4 mr-2" />
          Save Changes
        </Button>
        <Button variant="outline" onClick={handleReset}>
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
