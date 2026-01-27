import { useState } from 'react';
import { useAuthStore } from '@/lib/store/useAuthStore';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Lock, Mail, Loader2, ArrowRight, ShieldCheck } from 'lucide-react';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const login = useAuthStore((state) => state.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    try {
        // Login: User authentication with email and password
        // Uses the new /auth/login endpoint for proper user authentication
        
        // Dynamic import to avoid circular dependency
        const { API_CONFIGS } = await import('@/lib/api/client');
        const axios = (await import('axios')).default;
        
        interface TokenResponse {
            access_token: string;
            token_type: string;
        }

        // Use direct axios call to bypass auth interceptors that might attach stale tokens
        const response = await axios.post<TokenResponse>(
            `${API_CONFIGS[0].baseUrl}/auth/login`, 
            {
                email: email,
                password: password
            }, 
            {
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );

        if (response.data.access_token) {
            // Fetch user info from /auth/me endpoint
            try {
                const userResponse = await axios.get(
                    `${API_CONFIGS[0].baseUrl}/auth/me`,
                    {
                        headers: {
                            'Authorization': `Bearer ${response.data.access_token}`,
                            'Content-Type': 'application/json'
                        }
                    }
                );
                
                // Login with actual user data from backend
                login(response.data.access_token, {
                    id: userResponse.data.id.toString(),
                    name: userResponse.data.full_name || userResponse.data.username,
                    email: userResponse.data.email,
                    role: userResponse.data.role
                });
            } catch (userError) {
                // Fallback if /auth/me fails - login with basic info
                console.warn("Failed to fetch user info, using basic data:", userError);
                login(response.data.access_token, {
                    id: '1',
                    name: email.split('@')[0],
                    email: email,
                    role: 'user'
                });
            }
        } else {
              alert("Login failed: No token received");
        }
    } catch (error: any) {
        console.error("Authentication error:", error);
        const errorMessage = error.response?.data?.detail || error.message || 'Invalid credentials';
        alert(`Authentication failed: ${errorMessage}`);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 relative overflow-hidden">
      {/* Abstract Background Shapes */}
      <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-primary/10 rounded-full blur-[100px] animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-secondary/10 rounded-full blur-[100px] animate-pulse delay-1000" />

      <Card className="w-full max-w-md border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl relative z-10 animate-in fade-in zoom-in-95 duration-500">
        <CardHeader className="text-center space-y-2 pb-8">
          <div className="flex justify-center mb-4">
            <div className="p-3 rounded-2xl bg-gradient-to-br from-primary to-primary/50 shadow-lg shadow-primary/20">
                <ShieldCheck className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight bg-gradient-to-br from-foreground to-muted-foreground bg-clip-text text-transparent">
            Welcome Back
          </CardTitle>
          <CardDescription className="text-base">
            Authenticate to access the Omega Control Plane
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="relative group">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                <Input
                  type="email"
                  placeholder="name@omegakg.io"
                  className="pl-9 bg-background/50 border-white/5 focus:bg-background/80 transition-all duration-300"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="relative group">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                <Input
                  type="password"
                  placeholder="API Key (or Password)"
                  className="pl-9 bg-background/50 border-white/5 focus:bg-background/80 transition-all duration-300"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>
            
            {/* Registration removed to prevent invalid states */}
          </CardContent>
          <CardFooter className="flex flex-col gap-4 pt-4">
            <Button 
                type="submit" 
                className="w-full h-11 text-base font-medium shadow-lg shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98]" 
                disabled={isLoading || !email || !password}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Authenticating...
                </>
              ) : (
                <>
                  Sign In
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
            
            <div className="text-xs text-center text-muted-foreground space-y-2">
                <p>Authorized personnel only. All actions are logged.</p>
            </div>
          </CardFooter>
        </form>
      </Card>
      
      {/* Footer Branding */}
      <div className="absolute bottom-8 text-center">
        <p className="text-xs text-muted-foreground font-medium tracking-widest opacity-50">
            PRIMUS • CORTEX • BRIDGE
        </p>
      </div>
    </div>
  );
}
