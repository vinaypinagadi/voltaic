import React, { useState, useEffect } from 'react';
import { Sparkles, Eye, User, HeartHandshake, ShieldAlert } from 'lucide-react';
import { FanView } from './pages/FanView';
import { AdminCockpit } from './pages/AdminCockpit';

export const App: React.FC = () => {
  const [token, setToken] = useState<string | null>(localStorage.getItem('voltaic_token'));
  const [user, setUser] = useState<any | null>(JSON.parse(localStorage.getItem('voltaic_user') || 'null'));
  const [highContrast, setHighContrast] = useState<boolean>(
    localStorage.getItem('high_contrast') === 'true'
  );
  
  const [username, setUsername] = useState('');
  const [role, setRole] = useState<'fan' | 'staff' | 'admin'>('fan');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Apply high contrast styling to body
  useEffect(() => {
    if (highContrast) {
      document.body.classList.add('high-contrast');
    } else {
      document.body.classList.remove('high-contrast');
    }
    localStorage.setItem('high_contrast', highContrast.toString());
  }, [highContrast]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError('');
    try {
      let response;
      if (isSignUp) {
        response = await fetch('http://localhost:8000/api/auth/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            password,
            role,
            full_name: username || 'User',
            languages: role === 'staff' ? ['en', 'es'] : ['en']
          })
        });
      } else {
        response = await fetch('http://localhost:8000/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Authentication failed');
      }

      const data = await response.json();
      if (isSignUp) {
        // If it was signup, auto login the user
        const loginResponse = await fetch('http://localhost:8000/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        if (!loginResponse.ok) {
          throw new Error('Signup succeeded, but automatic login failed. Please sign in manually.');
        }
        const loginData = await loginResponse.json();
        setToken(loginData.access_token);
        setUser(loginData.user);
        localStorage.setItem('voltaic_token', loginData.access_token);
        localStorage.setItem('voltaic_user', JSON.stringify(loginData.user));
      } else {
        setToken(data.access_token);
        setUser(data.user);
        localStorage.setItem('voltaic_token', data.access_token);
        localStorage.setItem('voltaic_user', JSON.stringify(data.user));
      }
    } catch (err: any) {
      setAuthError(err.message || 'Failed to authenticate with backend server.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleDemoLogin = async (selectedRole: 'fan' | 'staff' | 'admin') => {
    setAuthLoading(true);
    setAuthError('');
    const demoEmails = {
      fan: 'vinay@voltaic.ai',
      staff: 'volunteer@voltaic.ai',
      admin: 'operator@voltaic.ai'
    };
    const demoNames = {
      fan: 'Vinay',
      staff: 'Volunteer',
      admin: 'Operator'
    };
    const email = demoEmails[selectedRole];
    const password = 'DemoPassword123!';
    const name = demoNames[selectedRole];
    
    try {
      // 1. Try to login
      let response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        // 2. If login fails, try to signup first (auto-registration)
        const signupResponse = await fetch('http://localhost:8000/api/auth/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            password,
            role: selectedRole,
            full_name: name,
            languages: selectedRole === 'staff' ? ['en', 'es'] : ['en']
          })
        });

        if (!signupResponse.ok) {
          const errData = await signupResponse.json().catch(() => ({}));
          throw new Error(errData.detail || 'Demo registration failed.');
        }

        // 3. Retry login after successful signup
        response = await fetch('http://localhost:8000/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
          throw new Error('Demo login failed after registration.');
        }
      }

      const data = await response.json();
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('voltaic_token', data.access_token);
      localStorage.setItem('voltaic_user', JSON.stringify(data.user));
    } catch (err: any) {
      setAuthError(err.message || 'Failed to connect for demo login.');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('voltaic_token');
    localStorage.removeItem('voltaic_user');
  };

  const handleRoleSelect = (selectedRole: 'fan' | 'staff' | 'admin') => {
    setRole(selectedRole);
  };

  return (
    <div className="app-container">
      {/* Background glow effects */}
      <div className="glow-bg glow-purple" />
      <div className="glow-bg glow-cyan" />

      {/* Global Header */}
      <header className="app-header">
        <div className="logo-container">
          <Sparkles style={{ color: 'var(--accent-cyan)' }} aria-hidden="true" />
          <span className="logo-text">Voltaic.AI</span>
          <span className="logo-tag">FIFA 26</span>
        </div>
        
        <div className="nav-buttons">
          <button 
            onClick={() => setHighContrast(!highContrast)} 
            className="btn btn-secondary"
            aria-label="Toggle high contrast accessibility mode"
            style={{ fontSize: '0.85rem' }}
          >
            <Eye size={16} /> 
            <span>{highContrast ? "Standard Mode" : "High Contrast"}</span>
          </button>
          
          {token && (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Session: <strong>{user?.full_name} ({user?.role?.toUpperCase()})</strong>
            </span>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      {!token ? (
        // Premium Login Screen
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
          <section className="card fade-in" style={{ width: '100%', maxWidth: '460px' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '0.5rem', textAlign: 'center', fontFamily: 'Outfit', fontWeight: 600 }}>
              FIFA World Cup 2026 Portal
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', marginBottom: '1.25rem' }}>
              Access the operations, volunteering, and waypoint platform
            </p>
            
            {/* Tab Toggles */}
            <div 
              style={{ display: 'flex', borderBottom: '1px solid var(--glass-border)', marginBottom: '1.25rem' }} 
              role="tablist" 
              aria-label="Authentication Actions"
            >
              <button
                id="signin-tab-button"
                type="button"
                role="tab"
                aria-selected={!isSignUp}
                aria-controls="auth-form-panel"
                onClick={() => { setIsSignUp(false); setAuthError(''); }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'none',
                  border: 'none',
                  color: !isSignUp ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  borderBottom: !isSignUp ? '2px solid var(--accent-cyan)' : 'none',
                  fontWeight: !isSignUp ? '600' : '400',
                  cursor: 'pointer',
                  fontSize: '0.95rem'
                }}
              >
                Sign In
              </button>
              <button
                id="signup-tab-button"
                type="button"
                role="tab"
                aria-selected={isSignUp}
                aria-controls="auth-form-panel"
                onClick={() => { setIsSignUp(true); setAuthError(''); }}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'none',
                  border: 'none',
                  color: isSignUp ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  borderBottom: isSignUp ? '2px solid var(--accent-cyan)' : 'none',
                  fontWeight: isSignUp ? '600' : '400',
                  cursor: 'pointer',
                  fontSize: '0.95rem'
                }}
              >
                Sign Up
              </button>
            </div>
            
            <form 
              id="auth-form-panel"
              role="tabpanel"
              aria-labelledby={isSignUp ? "signup-tab-button" : "signin-tab-button"}
              onSubmit={handleLogin} 
              style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}
            >
              <div>
                <label htmlFor="email-input" style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Email Address</label>
                <input 
                  id="email-input"
                  type="email" 
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  style={{ width: '100%', padding: '0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-main)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}
                  required
                />
              </div>

              <div>
                <label htmlFor="password-input" style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Password</label>
                <input 
                  id="password-input"
                  type="password" 
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{ width: '100%', padding: '0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-main)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}
                  required
                />
              </div>

              {isSignUp && (
                <div>
                  <label htmlFor="username-input" style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Full Name</label>
                  <input 
                    id="username-input"
                    type="text" 
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    placeholder="John Doe"
                    style={{ width: '100%', padding: '0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-main)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}
                    required
                  />
                </div>
              )}

              {isSignUp && (
                <div>
                  <span style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 500 }}>Assign Platform Role</span>
                  
                  <div className="role-card-grid" role="radiogroup" aria-label="Select match-day role">
                    <div 
                      className={`role-card ${role === 'fan' ? 'active' : ''}`}
                      onClick={() => handleRoleSelect('fan')}
                      role="radio"
                      aria-checked={role === 'fan'}
                      tabIndex={0}
                      onKeyDown={(e) => e.key === 'Enter' && handleRoleSelect('fan')}
                    >
                      <div className="role-card-icon">
                        <User size={20} />
                      </div>
                      <div>
                        <div style={{ fontWeight: '600', fontSize: '0.95rem' }}>Fan Portal</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>Wayfinding route planner & chat guide</div>
                      </div>
                    </div>

                    <div 
                      className={`role-card ${role === 'staff' ? 'active' : ''}`}
                      onClick={() => handleRoleSelect('staff')}
                      role="radio"
                      aria-checked={role === 'staff'}
                      tabIndex={0}
                      onKeyDown={(e) => e.key === 'Enter' && handleRoleSelect('staff')}
                    >
                      <div className="role-card-icon">
                        <HeartHandshake size={20} />
                      </div>
                      <div>
                        <div style={{ fontWeight: '600', fontSize: '0.95rem' }}>Volunteer Staff</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>Receive matched tasks and language alerts</div>
                      </div>
                    </div>

                    <div 
                      className={`role-card ${role === 'admin' ? 'active' : ''}`}
                      onClick={() => handleRoleSelect('admin')}
                      role="radio"
                      aria-checked={role === 'admin'}
                      tabIndex={0}
                      onKeyDown={(e) => e.key === 'Enter' && handleRoleSelect('admin')}
                    >
                      <div className="role-card-icon">
                        <ShieldAlert size={20} />
                      </div>
                      <div>
                        <div style={{ fontWeight: '600', fontSize: '0.95rem' }}>Command Center</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>Telemetry analytics & volunteer dispatcher</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <button 
                type="submit" 
                className="btn btn-primary" 
                style={{ width: '100%', padding: '0.85rem', marginTop: '0.5rem' }}
                disabled={authLoading}
              >
                {authLoading ? "Processing..." : isSignUp ? "Create Account" : "Sign In"}
              </button>

              {authError && (
                <div style={{ color: 'var(--danger)', fontSize: '0.85rem', textAlign: 'center', marginTop: '0.5rem' }}>
                  {authError}
                </div>
              )}
            </form>

            <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--glass-border)', paddingTop: '1.25rem' }}>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', marginBottom: '0.75rem', fontWeight: 500 }}>
                Or use Quick Demo Login (Auto-registers in Supabase)
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => handleDemoLogin('fan')}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '0.65rem', fontSize: '0.85rem', cursor: 'pointer' }}
                  disabled={authLoading}
                >
                  <User size={16} style={{ color: 'var(--accent-cyan)' }} />
                  <span>Sign In as Fan (Vinay)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoLogin('staff')}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '0.65rem', fontSize: '0.85rem', cursor: 'pointer' }}
                  disabled={authLoading}
                >
                  <HeartHandshake size={16} style={{ color: 'var(--success)' }} />
                  <span>Sign In as Volunteer (Staff)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoLogin('admin')}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '0.65rem', fontSize: '0.85rem', cursor: 'pointer' }}
                  disabled={authLoading}
                >
                  <ShieldAlert size={16} style={{ color: 'var(--accent-purple)' }} />
                  <span>Sign In as Command Center (Admin)</span>
                </button>
              </div>
            </div>
          </section>
        </div>
      ) : user?.role === 'fan' ? (
        <FanView 
          token={token} 
          user={user} 
          highContrast={highContrast} 
          onLogout={handleLogout} 
        />
      ) : (
        <AdminCockpit 
          token={token} 
          supabaseUrl="https://xukqjrntzlvfhhvjfbwm.supabase.co"
          supabaseAnonKey="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1a3Fqcm50emx2ZmhodmpmYndtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzNDg3MDcsImV4cCI6MjA5ODkyNDcwN30.8wzaamfmSYnCPAYc-oIJ98W5rID0r5SVFnKLBCC782g" 
          onLogout={handleLogout} 
        />
      )}

      {/* Footer */}
      <footer style={{ 
        textAlign: 'center', 
        padding: '1.5rem', 
        color: 'var(--text-muted)', 
        fontSize: '0.8rem', 
        borderTop: '1px solid var(--glass-border)',
        marginTop: 'auto' 
      }}>
        FIFA World Cup Stadium Systems. Powered by Gemini & Supabase Realtime.
      </footer>
    </div>
  );
};
export default App;
