import React, { useState } from 'react';
import { BackgroundPatterns, PatternType } from '@/components/ui/backgroundpatterns';
import { useSettingsStore } from '@/lib/store/useSettingsStore';
import { useAuthStore } from '@/lib/store/useAuthStore';
import {
  LayoutDashboard,
  FileText,
  Database,
  Settings,
  LogOut,
  Menu,
  X,
  User,
  Activity
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'omega', label: 'Omega API', icon: Activity },
  { id: 'ingest', label: 'InGest API', icon: Database },
  { id: 'memos', label: 'Memos API', icon: FileText },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Use Zustand selectors to subscribe to specific settings for reactivity
  const currentPattern = useSettingsStore(
    (state) => (state.settings.find(s => s.key === 'ui_pattern')?.value || 'circuit') as PatternType
  );
  const patternOpacity = useSettingsStore(
    (state) => (state.settings.find(s => s.key === 'ui_pattern_opacity')?.value || 0.03) as number
  );

  // Detect active page from hash
  const activePage = window.location.hash.slice(1) || 'dashboard';

  const handleNavigate = (page: string) => {
    window.location.hash = page;
    setSidebarOpen(false);
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-body flex overflow-hidden selection:bg-teal-500 selection:text-background">
      
      {/* Dynamic SVG Background Pattern */}
      <BackgroundPatterns pattern={currentPattern} opacity={patternOpacity} />
      
      {/* Optional gradient overlay for depth */}
      <div className="fixed inset-0 pointer-events-none z-0 bg-gradient-to-b from-teal-500/5 to-transparent h-[500px]" />

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-10 w-64 bg-card/95 backdrop-blur-sm border-r border-border transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-teal-500/20 rounded-lg flex items-center justify-center">
              <span className="text-teal-400 font-bold">Ω</span>
            </div>
            <span className="font-heading font-bold text-lg text-teal-400">CortexBridge</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-6">
          <ul className="space-y-2 px-4">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              
              return (
                <li key={item.id}>
                  <Button
                    variant={isActive ? "default" : "ghost"}
                    className={cn(
                      "w-full justify-start gap-3",
                      isActive && "bg-teal-500/20 text-teal-400 hover:bg-teal-500/30"
                    )}
                    onClick={() => handleNavigate(item.id)}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </Button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User Profile */}
        <div className="border-t border-border p-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-teal-500/20 flex items-center justify-center">
              <User className="h-5 w-5 text-teal-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.email || 'Guest'}</p>
              <p className="text-xs text-muted-foreground truncate">Administrator</p>
            </div>
          </div>
          <Button
            variant="outline"
            className="w-full justify-start gap-2"
            onClick={logout}
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col lg:ml-64">
        {/* Mobile Header */}
        <header className="lg:hidden h-16 bg-card/95 backdrop-blur-sm border-b border-border flex items-center justify-between px-4 z-10">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-teal-500/20 rounded-lg flex items-center justify-center">
              <span className="text-teal-400 font-bold">Ω</span>
            </div>
            <span className="font-heading font-bold text-teal-400">CortexBridge</span>
          </div>
          <div className="w-10" /> {/* Spacer for balance */}
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto relative z-10">
          <div className="container mx-auto px-4 py-6 max-w-7xl">
            {children}
          </div>
        </main>
      </div>

      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-10 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
};