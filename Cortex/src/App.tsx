import { useEffect, useState, Suspense, lazy } from 'react';
import { useSystemStore } from '@/lib/store/systemStore';
import { useAuthStore } from '@/lib/store/useAuthStore';
import { LoginPage } from '@/components/pages/LoginPage';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ViewSkeleton } from '@/components/ui/skeleton-loader';
import { ToastContainer } from '@/components/ui/toast';

// Lazy load feature components
const Dashboard = lazy(() => import('@/components/Dashboard').then(module => ({ default: module.Dashboard })));
const CaptureControl = lazy(() => import('@/components/features/capture/CaptureControl').then(module => ({ default: module.CaptureControl })));
const IngestControl = lazy(() => import('@/components/features/ingest/IngestControl').then(module => ({ default: module.IngestControl })));
const MemosControl = lazy(() => import('@/components/features/memos/MemosControl').then(module => ({ default: module.MemosControl })));
const SettingsPage = lazy(() => import('@/components/pages/SettingsPage').then(module => ({ default: module.SettingsPage })));

export default App;

function App() {
  const { theme } = useSystemStore();
  const { isAuthenticated } = useAuthStore();
  const [currentView, setCurrentView] = useState('dashboard');

  useEffect(() => {
    // Theme application
    if (theme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  }, [theme]);

  // Auth Protection - Use useEffect to react to auth state changes
  useEffect(() => {
    if (!isAuthenticated) {
      // Clear hash when not authenticated
      if (window.location.hash) {
        window.location.hash = '';
      }
    }
  }, [isAuthenticated]);

  // Auth Protection
  if (!isAuthenticated) {
    return (
        <div className={theme === 'light' ? 'light' : ''}>
            <LoginPage />
        </div>
    );
  }

  useEffect(() => {
    // Simple hash routing
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1) || 'dashboard';
      setCurrentView(hash);
    };

    window.addEventListener('hashchange', handleHashChange);
    // Initial check
    handleHashChange();

    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const renderContent = () => {
    return (
      <Suspense fallback={<ViewSkeleton />}>
        {(() => {
            switch (currentView) {
            case 'omega':
                return <CaptureControl />;
            case 'ingest':
                return <IngestControl />;
            case 'memos':
                return <MemosControl />;
            case 'settings':
                return <SettingsPage />;
            case 'dashboard':
            default:
                return <Dashboard />;
            }
        })()}
      </Suspense>
    );
  };

  return (
    <>
      <DashboardLayout>
        {renderContent()}
      </DashboardLayout>
      <ToastContainer />
    </>
  );
}
