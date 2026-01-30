import { ReactNode } from 'react';
import {
  LayoutDashboard,
  Activity,
  Database,
  FileText,
  Settings,
  Menu,
  X,
  Sun,
  Moon,
  LogOut,
  Cpu,
  Power,
  RotateCcw,
  Brain
} from 'lucide-react';
import { SystemHUD } from '@/components/common/SystemHUD';
import { useSystemStore } from '@/lib/store/systemStore';
import { useAuthStore } from '@/lib/store/useAuthStore';
import { useSettingsStore } from '@/lib/store/useSettingsStore';
import { useToastStore } from '@/lib/store/useToastStore';
import { captureApi } from '@/lib/api/client';
import { BackgroundPatterns, PatternType } from '@/components/ui/backgroundpatterns';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertBanner } from '@/components/ui/alert-banner';

interface DashboardLayoutProps {
  children: ReactNode;
}

const navigation = [
  { name: 'Dashboard', icon: LayoutDashboard, href: '#dashboard' },
  { name: 'Cortex Bridge', icon: Brain, href: '#cortex' },
  { name: 'Omega API', icon: Activity, href: '#omega' },
  { name: 'InGest API', icon: Database, href: '#ingest' },
  { name: 'Memos API', icon: FileText, href: '#memos' },
  { name: 'Settings', icon: Settings, href: '#settings' },
];

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { sidebarCollapsed, toggleSidebar, systemStatus, theme, toggleTheme } = useSystemStore();
  const { user, logout } = useAuthStore();
  const { addToast } = useToastStore();

  const handleShutdown = async (e: React.MouseEvent) => {
    const isFull = e.shiftKey;
    const message = isFull 
      ? 'EMERGENCY SHUTDOWN: Are you sure you want to stop EVERYTHING, including Docker databases?' 
      : 'SAFE SHUTDOWN: Are you sure you want to stop all application services? (Databases will remain active)';

    if (window.confirm(message)) {
      try {
        await captureApi.shutdownEcosystem(isFull);
        addToast(`${isFull ? 'Full' : 'Safe'} shutdown initiated. Dashboard will disconnect soon.`, 'info');
      } catch (err) {
        console.error('Shutdown failed:', err);
        addToast('Failed to trigger system shutdown', 'error');
      }
    }
  };

  const handleRestart = async () => {
    if (window.confirm('Are you sure you want to RESTART the entire OmegaKG ecosystem? All applications will be stopped and restarted.')) {
      try {
        await captureApi.restartEcosystem();
        addToast('Restart sequence initiated. Dashboard will disconnect briefly.', 'info');
        // Optionally redirect to a "Restarting..." page or just let health checks fail and poller handle it
      } catch (err) {
        console.error('Restart failed:', err);
        addToast('Failed to trigger system restart', 'error');
      }
    }
  };

  // Use Zustand selectors to subscribe to specific settings for reactivity
  const currentPattern = useSettingsStore(
    (state) => (state.settings.find(s => s.key === 'ui_pattern')?.value || 'circuit') as PatternType
  );
  const patternOpacity = useSettingsStore(
    (state) => (state.settings.find(s => s.key === 'ui_pattern_opacity')?.value || 0.03) as number
  );

  const getStatusBadge = () => {
    switch (systemStatus) {
      case 'online':
        return <Badge variant="outline" className="border-emerald-500/50 text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 shadow-tech-sm transition-all duration-300">Online</Badge>;
      case 'degraded':
        return <Badge variant="outline" className="border-amber-500/50 text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 shadow-tech-sm transition-all duration-300">Degraded</Badge>;
      case 'offline':
        return <Badge variant="destructive" className="animate-pulse shadow-tech-md">Offline</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden text-foreground">
      {/* Dynamic SVG Background Pattern */}
      <BackgroundPatterns pattern={currentPattern} opacity={patternOpacity} />
      {/* Sidebar - Tech Panel Style */}
      <aside
        className={`${
          sidebarCollapsed ? 'w-20' : 'w-72'
        } bg-card glass-panel border-r border-teal-500/10 relative transition-all duration-300 flex flex-col z-50`}
      >
        {/* Glow Line */}
        <div className="absolute top-0 right-0 w-[1px] h-full bg-gradient-to-b from-transparent via-teal-500/30 to-transparent opacity-50"></div>

        {/* Sidebar Header */}
        <div className="h-20 flex items-center justify-between px-6 border-b border-border/30">
          {!sidebarCollapsed && (
            <div className="flex items-center space-x-3 group cursor-pointer">
              <div className="relative">
                <div className="w-10 h-10 bg-teal-500/10 rounded-lg border border-teal-500/20 flex items-center justify-center group-hover:border-teal-500/50 group-hover:shadow-[0_0_15px_rgba(0,191,166,0.3)] transition-all duration-300">
                  <Cpu className="w-6 h-6 text-teal-400" />
                </div>
                {/* Status Dot */}
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-teal-500 rounded-full shadow-[0_0_8px_rgba(0,191,166,0.8)] animate-pulse"></div>
              </div>
              <div className="flex flex-col">
                <span className="text-foreground font-bold text-lg group-hover:text-teal-400 transition-colors pointer-events-none select-none italic tracking-tighter">APEX<span className="text-teal-500 font-black">SIGMA</span></span>
                <span className="text-[10px] text-teal-600/80 uppercase tracking-widest font-mono">Control Plane</span>
              </div>
            </div>
          )}
          <button
            onClick={toggleSidebar}
            className={`p-2 rounded-lg hover:bg-teal-500/10 text-teal-400/70 hover:text-teal-400 transition-all duration-300 ${sidebarCollapsed ? 'mx-auto' : ''}`}
          >
            {sidebarCollapsed ? <Menu size={24} /> : <X size={20} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-8 space-y-2">
          {navigation.map((item) => {
            const isActive = window.location.hash === item.href || (window.location.hash === '' && item.href === '#dashboard');
            return (
              <a
                key={item.name}
                href={item.href}
                className={`
                  group flex items-center gap-4 px-4 py-3 rounded-lg transition-all duration-200
                  border border-transparent hover:border-teal-500/30
                  ${isActive 
                    ? 'bg-gradient-to-r from-teal-500/20 to-transparent border-teal-500/30 text-teal-400' 
                    : 'text-foreground/70 hover:bg-teal-500/10 hover:text-teal-500'}
                `}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon size={22} className={`${isActive ? 'text-teal-400 drop-shadow-[0_0_5px_rgba(0,191,166,0.5)]' : 'group-hover:text-teal-400 group-hover:drop-shadow-[0_0_5px_rgba(0,191,166,0.5)]'} transition-all`} />
                {!sidebarCollapsed && <span className="font-black tracking-[0.1em] uppercase text-[11px] italic">{item.name}</span>}
                
                {/* Active Indicator Glow */}
                {isActive && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-teal-400 shadow-[0_0_8px_teal] animate-pulse"></div>
                )}
              </a>
            );
          })}
        </nav>

        {/* System Status Footer */}
        <div className="p-6 border-t border-border/30 bg-black/5">
          {!sidebarCollapsed ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-[10px] text-teal-500/70 uppercase font-mono tracking-widest font-bold">
                  System Cluster
                </div>
                <div className="text-[10px] text-muted-foreground font-mono">V_2.5</div>
              </div>
              {getStatusBadge()}
            </div>
          ) : (
            <div className="flex justify-center">{getStatusBadge()}</div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto relative">
        {/* Top Vignette Overlay */}
        <div className="fixed top-0 left-0 w-full h-32 bg-gradient-to-b from-black/5 to-transparent dark:from-black/40 pointer-events-none z-40"></div>

        {/* Header - Floating HUD Style */}
        <header className="sticky top-0 z-30 px-8 py-6">
          <div className="bg-card glass-panel border border-teal-500/10 rounded-2xl shadow-lg flex items-center justify-between p-4 pl-6">
            <h1 className="text-xl font-black italic tracking-tighter text-foreground uppercase">
              Command <span className="text-teal-500">Center</span>
            </h1>
            
            <div className="flex items-center gap-4">
              {/* System HUD - Vitals Telemetry */}
              <SystemHUD />
              
              <div className="h-8 w-[1px] bg-border mx-1"></div>
              
              <div className="hidden md:flex flex-col items-end mr-2">
                <span className="text-sm font-black tracking-tighter text-foreground uppercase italic">{user?.email || 'admin@omegakg.io'}</span>
                 <span className="text-[10px] text-teal-500 uppercase tracking-[0.3em] font-black italic">SUPERUSER</span>
              </div>
              
              <div className="h-8 w-[1px] bg-border mx-1"></div>

              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleRestart}
                  className="rounded-full hover:bg-amber-500/10 hover:text-amber-500 transition-colors"
                  title="Restart Ecosystem"
                >
                  <RotateCcw size={18} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleShutdown}
                  className="rounded-full hover:bg-red-500/10 hover:text-red-500 transition-colors shadow-[0_0_10px_rgba(239,68,68,0)] hover:shadow-[0_0_15px_rgba(239,68,68,0.3)]"
                  title="Shutdown Ecosystem (Shift+Click for FULL shutdown)"
                >
                  <Power size={18} />
                </Button>
                <div className="h-4 w-[1px] bg-border mx-1 self-center"></div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  className="rounded-full hover:bg-teal-500/10 hover:text-teal-400 transition-colors"
                  title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                >
                  {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={logout}
                  className="rounded-full hover:bg-red-500/10 hover:text-red-500 transition-colors"
                  title="Sign Out"
                >
                  <LogOut size={18} />
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="px-8 pb-8 max-w-[1920px] mx-auto">
          <AlertBanner />
          <div className="mt-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
