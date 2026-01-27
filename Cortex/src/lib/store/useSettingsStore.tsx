import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Setting {
  key: string;
  label: string;
  value: string | number | boolean;
  type: 'text' | 'number' | 'boolean' | 'select';
  section: 'general' | 'appearance' | 'integrations' | 'advanced';
  description?: string;
  options?: string[];
  defaultValue?: any;
}

interface SettingsStore {
  settings: Setting[];
  updateSetting: (key: string, value: any) => void;
  resetSettings: () => void;
}

const INITIAL_SETTINGS: Setting[] = [
  // General
  {
    key: 'project_name',
    label: 'Project Name',
    type: 'text',
    value: 'CortexBridge',
    defaultValue: 'CortexBridge',
    section: 'general',
    description: 'Display name for your project'
  },
  
  // Appearance
  {
    key: 'ui_pattern',
    label: 'Background Pattern',
    type: 'select',
    value: 'circuit',
    defaultValue: 'circuit',
    options: ['geometric', 'circuit', 'wave', 'grid', 'none'],
    description: 'Select the ambient background texture for the dashboard',
    section: 'appearance'
  },
  {
    key: 'ui_pattern_opacity',
    label: 'Pattern Opacity',
    type: 'number',
    value: 0.03,
    defaultValue: 0.03,
    description: 'Background pattern opacity (0.0 - 1.0)',
    section: 'appearance'
  },
  
  // Integrations
  {
    key: 'linear_api_key',
    label: 'Linear API Key',
    type: 'text',
    value: '',
    defaultValue: '',
    section: 'integrations',
    description: 'API key for Linear integration'
  },
  {
    key: 'neo4j_uri',
    label: 'Neo4j URI',
    type: 'text',
    value: 'bolt://localhost:7687',
    defaultValue: 'bolt://localhost:7687',
    section: 'integrations',
    description: 'Neo4j database connection URI'
  },
  
  // Advanced
  {
    key: 'debug_mode',
    label: 'Debug Mode',
    type: 'boolean',
    value: false,
    defaultValue: false,
    section: 'advanced',
    description: 'Enable verbose logging'
  },
  {
    key: 'auto_refresh',
    label: 'Auto Refresh Interval (seconds)',
    type: 'number',
    value: 30,
    defaultValue: 30,
    section: 'advanced',
    description: 'Dashboard data refresh interval'
  }
];

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      settings: INITIAL_SETTINGS,
      
      updateSetting: (key: string, value: any) => 
        set((state) => ({
          settings: state.settings.map((setting) =>
            setting.key === key ? { ...setting, value } : setting
          )
        })),
      
      resetSettings: () => 
        set({
          settings: INITIAL_SETTINGS.map(s => ({ ...s, value: s.defaultValue }))
        })
    }),
    {
      name: 'cortexbridge-settings'
    }
  )
);
// ...