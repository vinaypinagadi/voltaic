import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Ticket as TicketIcon, 
  Volume2, 
  ShieldAlert, 
  MessageSquare,
  Compass,
  Accessibility,
  AlertCircle
} from 'lucide-react';
import AriaLiveAlert from '../components/AriaLiveAlert';

interface Message {
  role: 'user' | 'model';
  content: string;
  isEmergency?: boolean;
}

interface FanViewProps {
  token: string;
  user: any;
  highContrast: boolean;
  onLogout: () => void;
}

export const FanView: React.FC<FanViewProps> = ({ token, user, highContrast, onLogout }) => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'model', content: `Welcome ${user?.full_name || 'Fan'} to the FIFA World Cup 2026. I am Voltaic.AI, your interactive stadium guide. Ask me anything about seat locations, entry gates, schedules, or rules.` }
  ]);
  
  useEffect(() => {
    if (highContrast) {
      console.log('High contrast styling enabled for Fan View.');
    }
  }, [highContrast]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [accessibleRoute, setAccessibleRoute] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  const [activeTab, setActiveTab] = useState<'chat' | 'map'>('chat');
  
  // Mock gate wait times
  const [gateCongestion] = useState({
    'Gate A': { wait: '3 mins', status: 'low' },
    'Gate B': { wait: '18 mins', status: 'high' },
    'Gate C': { wait: '6 mins', status: 'low' },
    'Gate D': { wait: '25 mins', status: 'critical' },
  });

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    const history = messages.slice(1).map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    try {
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userMessage,
          history: history
        })
      });

      if (!response.ok) {
        throw new Error('API server returned error');
      }

      setMessages(prev => [...prev, { role: 'model', content: '' }]);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');
      
      if (!reader) {
        throw new Error('Streaming failed to initialize');
      }

      let concatenatedResponse = '';
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        concatenatedResponse += chunk;
        
        setMessages(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last && last.role === 'model') {
            last.content = concatenatedResponse;
            if (concatenatedResponse.includes('EMERGENCY PROTOCOL') || concatenatedResponse.includes('HAZARD PROTOCOL') || concatenatedResponse.includes('CROWD EMERGENCY')) {
              last.isEmergency = true;
            }
          }
          return updated;
        });
      }

      if (concatenatedResponse.includes('EMERGENCY PROTOCOL') || concatenatedResponse.includes('HAZARD')) {
        setAnnouncement('Critical Warning: Emergency dispatch has been notified. Stay where you are.');
      }

    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { role: 'model', content: 'Connection issue. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="fade-in" style={{ padding: '1rem', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
      <AriaLiveAlert message={announcement} type="assertive" />

      {/* Premium Ticket Card */}
      <section className="card" style={{ marginBottom: '1.25rem', borderLeft: '4px solid var(--accent-cyan)' }}>
        <h2 style={{ fontSize: '1.1rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
          <TicketIcon style={{ color: 'var(--accent-cyan)' }} size={18} aria-hidden="true" />
          <span>Match-Day Seating & Gate Info</span>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem', fontSize: '0.9rem' }}>
          <div><span style={{ color: 'var(--text-muted)' }}>Event:</span> USA vs ARG</div>
          <div><span style={{ color: 'var(--text-muted)' }}>Gate Entry:</span> Gate C (Low Congestion)</div>
          <div><span style={{ color: 'var(--text-muted)' }}>Seat Section:</span> Section 102</div>
          <div><span style={{ color: 'var(--text-muted)' }}>Row & Seat:</span> Row M, Seat 14</div>
        </div>
      </section>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }} role="tablist" aria-label="Fan navigation tabs">
        <button 
          id="chat-tab-button"
          role="tab"
          aria-selected={activeTab === 'chat'}
          aria-controls="chat-tab-panel"
          className={`btn ${activeTab === 'chat' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('chat')}
          style={{ flex: 1, gap: '6px' }}
        >
          <MessageSquare size={16} aria-hidden="true" />
          <span>Fan Chat Assistant</span>
        </button>
        <button 
          id="map-tab-button"
          role="tab"
          aria-selected={activeTab === 'map'}
          aria-controls="map-tab-panel"
          className={`btn ${activeTab === 'map' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('map')}
          style={{ flex: 1, gap: '6px' }}
        >
          <Compass size={16} aria-hidden="true" />
          <span>Stadium Navigation</span>
        </button>
      </div>

      {/* TAB A: Chat */}
      {activeTab === 'chat' && (
        <section 
          id="chat-tab-panel"
          role="tabpanel"
          aria-labelledby="chat-tab-button"
          className="card chat-container"
        >
          <div className="chat-history" role="log">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`chat-bubble ${msg.role} ${msg.isEmergency ? 'emergency' : ''}`}
                style={{
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}
              >
                {msg.isEmergency && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 'bold', fontSize: '0.8rem', color: 'var(--danger)' }}>
                    <ShieldAlert size={14} /> Emergency services dispatched
                  </div>
                )}
                <span>{msg.content}</span>
              </div>
            ))}
            {loading && (
              <div className="chat-bubble model" style={{ fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Volume2 size={16} className="pulse-card" />
                <span>Voltaic.AI is generating stream...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="chat-input-bar">
            <label htmlFor="chat-input-field" className="visually-hidden">Ask stadium assistant a question</label>
            <input 
              id="chat-input-field"
              type="text" 
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask: 'Where is section 102?' or type 'medical emergency'"
              disabled={loading}
            />
            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ padding: '0 1.25rem' }} 
              aria-label="Send message"
              disabled={loading}
            >
              <Send size={16} aria-hidden="true" />
            </button>
          </form>
        </section>
      )}

      {/* TAB B: Wayfinding Map */}
      {activeTab === 'map' && (
        <section 
          id="map-tab-panel"
          role="tabpanel"
          aria-labelledby="map-tab-button"
          className="card fade-in"
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Congestion-Aware Wayfinding</h2>
            <button onClick={onLogout} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem', height: 'auto' }}>
              Sign Out
            </button>
          </div>

          {/* Accessible Custom Toggle Switch */}
          <div style={{ display: 'flex', alignItems: 'center', padding: '0.85rem', background: 'var(--bg-hover)', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', border: '1px solid var(--glass-border)' }}>
            <label className="switch-container">
              <input 
                type="checkbox" 
                className="switch-input"
                id="accessible-route-toggle" 
                checked={accessibleRoute}
                onChange={e => {
                  setAccessibleRoute(e.target.checked);
                  setAnnouncement(e.target.checked ? "Routing engine set to accessible elevators and ramps." : "Standard route selected.");
                }}
              />
              <span className="switch-slider"></span>
              <span style={{ fontSize: '0.9rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Accessibility size={16} style={{ color: 'var(--accent-cyan)' }} />
                <span>Require Accessible Pathway (Ramps / Elevators)</span>
              </span>
            </label>
          </div>

          {/* Dynamic SVG-based Wayfinding Map */}
          <div className="wayfinding-map" style={{ height: '380px' }}>
            <svg viewBox="0 0 500 350" style={{ width: '100%', height: '100%', background: 'var(--bg-primary)' }} aria-label="Visual Stadium Map">
              <defs>
                <radialGradient id="pitchGlow" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor="rgba(139, 92, 246, 0.25)" />
                  <stop offset="100%" stopColor="rgba(10, 15, 29, 0)" />
                </radialGradient>
              </defs>

              {/* Pitch Ring Center */}
              <ellipse cx="250" cy="175" rx="100" ry="65" fill="url(#pitchGlow)" stroke="rgba(139, 92, 246, 0.4)" strokeWidth="1.5" />
              <ellipse cx="250" cy="175" rx="90" ry="58" fill="none" stroke="rgba(139, 92, 246, 0.2)" strokeWidth="1" strokeDasharray="3 3" />
              <text x="250" y="178" fill="var(--text-muted)" fontSize="9" letterSpacing="2" textAnchor="middle">FIELD CENTER</text>

              {/* Lower Tier Rings */}
              <ellipse cx="250" cy="175" rx="160" ry="105" fill="none" stroke="var(--glass-border)" strokeWidth="2" />
              {/* Outer Concourse Ring */}
              <ellipse cx="250" cy="175" rx="205" ry="135" fill="none" stroke="var(--glass-border)" strokeWidth="1" />

              {/* Gates Circles and Text */}
              {/* Gate A (Top Left) */}
              <circle cx="85" cy="75" r="14" fill="var(--bg-secondary)" stroke="var(--success)" strokeWidth="2" />
              <text x="85" y="79" fill="var(--success)" fontSize="8" fontWeight="bold" textAnchor="middle">GA</text>
              <text x="85" y="52" fill="var(--text-muted)" fontSize="8" textAnchor="middle">Gate A (3m)</text>

              {/* Gate B (Top Right - Congested) */}
              <circle cx="415" cy="75" r="14" fill="var(--bg-secondary)" stroke="var(--danger)" strokeWidth="2" />
              <text x="415" y="79" fill="var(--danger)" fontSize="8" fontWeight="bold" textAnchor="middle">GB</text>
              <text x="415" y="52" fill="var(--text-muted)" fontSize="8" textAnchor="middle">Gate B (18m)</text>

              {/* Gate C (Bottom Left) */}
              <circle cx="85" cy="275" r="14" fill="var(--bg-secondary)" stroke="var(--success)" strokeWidth="2" />
              <text x="85" y="279" fill="var(--success)" fontSize="8" fontWeight="bold" textAnchor="middle">GC</text>
              <text x="85" y="299" fill="var(--text-muted)" fontSize="8" textAnchor="middle">Gate C (6m)</text>

              {/* Gate D (Bottom Right - Congested) */}
              <circle cx="415" cy="275" r="14" fill="var(--bg-secondary)" stroke="var(--danger)" strokeWidth="2" />
              <text x="415" y="279" fill="var(--danger)" fontSize="8" fontWeight="bold" textAnchor="middle">GD</text>
              <text x="415" y="299" fill="var(--text-muted)" fontSize="8" textAnchor="middle">Gate D (25m)</text>

              {/* Section 102 Destination block */}
              <rect x="225" y="32" width="50" height="24" rx="4" fill="var(--accent-cyan)" />
              <text x="250" y="47" fill="var(--text-inverse)" fontSize="9" fontWeight="bold" textAnchor="middle">SEC 102</text>

              {/* Accessible Node / Ramp Indicator */}
              {accessibleRoute ? (
                <>
                  <circle cx="160" cy="235" r="10" fill="var(--bg-secondary)" stroke="var(--success)" strokeWidth="1.5" />
                  <path d="M157 232h3v4h-3z" fill="var(--success)" />
                  <text x="160" y="252" fill="var(--success)" fontSize="7" textAnchor="middle">RAMP</text>
                  
                  {/* Route path through Accessible Ramp */}
                  <path 
                    d="M 85,275 C 120,275 160,250 160,235 C 160,200 180,95 225,44" 
                    fill="none" 
                    stroke="var(--success)" 
                    strokeWidth="4" 
                    strokeLinecap="round" 
                    className="animated-path"
                  />
                </>
              ) : (
                <>
                  <circle cx="160" cy="115" r="10" fill="var(--bg-secondary)" stroke="var(--accent-cyan)" strokeWidth="1.5" />
                  <text x="160" y="119" fill="var(--accent-cyan)" fontSize="7" fontWeight="bold" textAnchor="middle">ST</text>
                  <text x="160" y="132" fill="var(--accent-cyan)" fontSize="7" textAnchor="middle">STAIRS</text>

                  {/* Route path through Standard Stairs */}
                  <path 
                    d="M 85,275 C 100,200 130,115 160,115 C 190,115 210,60 225,44" 
                    fill="none" 
                    stroke="var(--accent-cyan)" 
                    strokeWidth="4" 
                    strokeLinecap="round" 
                    className="animated-path"
                  />
                </>
              )}
            </svg>
          </div>

          {/* Congestion Info panel */}
          <div style={{ marginTop: '1.5rem' }}>
            <h3 style={{ fontSize: '0.95rem', marginBottom: '0.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertCircle size={14} style={{ color: 'var(--warning)' }} />
              <span>Live Gate Entry Waiting Times</span>
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', fontSize: '0.8rem' }}>
              {Object.entries(gateCongestion).map(([gate, details]) => (
                <div key={gate} style={{ 
                  background: details.status === 'low' ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)', 
                  border: `1px solid ${details.status === 'low' ? 'var(--success)' : 'var(--danger)'}`,
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.5rem',
                  textAlign: 'center'
                }}>
                  <div style={{ fontWeight: '600' }}>{gate}</div>
                  <div style={{ color: details.status === 'low' ? 'var(--success)' : 'var(--danger)', fontWeight: 'bold', marginTop: '2px' }}>{details.wait}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </main>
  );
};
export default FanView;
