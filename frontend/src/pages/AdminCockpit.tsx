import React, { useState, useEffect, useCallback } from 'react';
import { createClient, RealtimePostgresChangesPayload } from '@supabase/supabase-js';
import { 
  AlertOctagon, 
  Activity, 
  TrendingUp, 
  Navigation, 
  Languages, 
  UserCheck, 
  RefreshCw, 
  Clock, 
  Sliders, 
  MapPin, 
  User, 
  Radio
} from 'lucide-react';
import AriaLiveAlert from '../components/AriaLiveAlert';

export interface Alert {
  id: string;
  title: string;
  description: string;
  category: string;
  status: string;
  location: string;
  severity: string;
  created_at: string;
}

export interface Suggestion {
  staff_id: string;
  full_name: string;
  distance_meters: number;
  languages: string[];
}

interface AdminCockpitProps {
  token: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  onLogout: () => void;
}

export const AdminCockpit: React.FC<AdminCockpitProps> = React.memo(({ token, supabaseUrl, supabaseAnonKey, onLogout }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [announcement, setAnnouncement] = useState('');
  
  // Telemetry Form State
  const [gateName, setGateName] = useState('Gate B');
  const [entryRate, setEntryRate] = useState(135.0);
  const [waitTime, setWaitTime] = useState(20.0);
  const [density, setDensity] = useState('high');
  const [telemetryMessage, setTelemetryMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize optional Supabase client for realtime connection
  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    global: { headers: { Authorization: `Bearer ${token}` } }
  });

  // Load alerts and subscribe to Supabase Realtime
  useEffect(() => {
    fetchAlerts();

    // Subscribe to realtime database inserts for real-time operation
    const channel = supabase.channel('realtime_alerts')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'staff_alerts' },
        (payload: RealtimePostgresChangesPayload<{ [key: string]: string | number | boolean | null }>) => {
          console.log('Realtime change received:', payload);
          fetchAlerts(); // Refresh logs on any database change
          if (payload.eventType === 'INSERT') {
            const newAlert = payload.new as unknown as Alert;
            if (newAlert) {
              setAnnouncement(`ALERT BROADCAST: ${newAlert.title} reported at ${newAlert.location}`);
            }
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [supabaseUrl, supabaseAnonKey, token]);

  // Fetch suggestions when an alert is selected
  useEffect(() => {
    if (selectedAlert) {
      fetchSuggestions(selectedAlert.id);
    } else {
      setSuggestions([]);
    }
  }, [selectedAlert]);

  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/dispatch/alerts', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setAlerts(data);
      }
    } catch (err) {
      console.error("Failed to fetch alerts: ", err);
    }
  }, [token]);

  const fetchSuggestions = useCallback(async (alertId: string) => {
    setSuggestLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/dispatch/suggestions/${alertId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      if (data && data.suggestions) {
        setSuggestions(data.suggestions);
      }
    } catch (e) {
      console.error("Failed to load dispatch suggestions: ", e);
    } finally {
      setSuggestLoading(false);
    }
  }, [token]);

  const handlePostTelemetry = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setTelemetryMessage('Ingesting data stream...');
    try {
      const response = await fetch('http://localhost:8000/api/telemetry', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          gate_name: gateName,
          entry_rate: parseFloat(entryRate.toString()),
          queue_wait_time: parseFloat(waitTime.toString()),
          crowd_density: density
        })
      });
      const data = await response.json();
      if (data.status === 'success') {
        setIsSubmitting(false);
        setTelemetryMessage(
          data.bottleneck_detected 
            ? 'Bottleneck warning generated and dispatched to field staff.' 
            : 'Entry flow recorded successfully. Metrics are within normal limits.'
        );
        fetchAlerts(); // Refresh logs
      } else {
        setIsSubmitting(false);
        setTelemetryMessage('Failed to record telemetry.');
      }
    } catch (err) {
      setIsSubmitting(false);
      setTelemetryMessage('Connection failed. Server offline.');
    }
  }, [gateName, entryRate, waitTime, density, fetchAlerts, token]);

  const handleDispatch = useCallback(async (staffId: string) => {
    if (!selectedAlert) return;
    try {
      const response = await fetch('http://localhost:8000/api/dispatch/assign', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          alert_id: selectedAlert.id,
          staff_id: staffId
        })
      });
      if (response.ok) {
        setAnnouncement(`Dispatched volunteer to ${selectedAlert.location}`);
        setSelectedAlert(null);
        fetchAlerts();
      }
    } catch (err) {
      console.error(err);
    }
  }, [selectedAlert, token, fetchAlerts]);

  return (
    <main className="fade-in" style={{ padding: '2rem', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
      <AriaLiveAlert message={announcement} type="assertive" />
      
      {/* Top Banner Dashboard */}
      <section style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', borderBottom: '1px solid var(--glass-border)', paddingBottom: '1.25rem' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 700, fontFamily: 'Outfit', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Activity style={{ color: 'var(--accent-cyan)' }} aria-hidden="true" />
            <span>World Cup Operations Cockpit</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>
            Real-time multimodal telemetry flow, bottleneck analysis, and dispatch routing
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button onClick={onLogout} className="btn btn-secondary">Sign Out</button>
        </div>
      </section>

      {/* Numerical Indicators (KPIs) */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid var(--accent-cyan)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>
            <span>Active Incidents</span>
            <AlertOctagon size={16} style={{ color: 'var(--danger)' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '8px', fontFamily: 'Outfit' }}>
            {alerts.filter(a => a.status === 'pending').length}
          </div>
        </div>
        <div className="card" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid var(--success)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>
            <span>Dispatched Staff</span>
            <UserCheck size={16} style={{ color: 'var(--success)' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '8px', fontFamily: 'Outfit' }}>
            {alerts.filter(a => a.status === 'dispatched').length}
          </div>
        </div>
        <div className="card" style={{ padding: '1rem 1.25rem', borderLeft: '4px solid var(--accent-purple)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase' }}>
            <span>Gate Flow Velocity</span>
            <TrendingUp size={16} style={{ color: 'var(--accent-purple)' }} />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '8px', fontFamily: 'Outfit' }}>
            118 <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>fans/min</span>
          </div>
        </div>
      </section>

      {/* Grid Dashboard */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
        
        {/* Metric Ingestion Controller */}
        <section className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
            <Sliders style={{ color: 'var(--accent-cyan)' }} size={20} />
            <span>Telemetry Controller</span>
          </h2>
          
          <form onSubmit={handlePostTelemetry} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', flex: 1 }}>
            <div>
              <label htmlFor="gate-select" style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Select Target Gate</label>
              <select 
                id="gate-select"
                value={gateName} 
                onChange={e => setGateName(e.target.value)}
                style={{ width: '100%', padding: '0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-main)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}
              >
                <option value="Gate A">Gate A (US Fan Entryway)</option>
                <option value="Gate B">Gate B (North Corridor - Heavy Transit)</option>
                <option value="Gate C">Gate C (Standard Lower Deck Access)</option>
                <option value="Gate D">Gate D (South Accessible Elevator Ramp)</option>
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label htmlFor="entry-rate-input" style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Entry Flow Rate (fans/min)</label>
                <input 
                  id="entry-rate-input"
                  type="number" 
                  step="0.1" 
                  value={entryRate} 
                  onChange={e => setEntryRate(parseFloat(e.target.value))}
                  style={{ width: '100%', padding: '0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-main)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}
                  required
                />
              </div>
              <div>
                <label htmlFor="wait-time-input" style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Queue Wait Time (mins)</label>
                <input 
                  id="wait-time-input"
                  type="number" 
                  step="0.1" 
                  value={waitTime} 
                  onChange={e => setWaitTime(parseFloat(e.target.value))}
                  style={{ width: '100%', padding: '0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-main)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="density-select" style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Crowd Density Density Class</label>
              <select 
                id="density-select"
                value={density} 
                onChange={e => setDensity(e.target.value)}
                style={{ width: '100%', padding: '0.75rem', background: 'var(--bg-secondary)', color: 'var(--text-main)', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-sm)', fontSize: '0.95rem' }}
              >
                <option value="low">Low Flow (Green)</option>
                <option value="medium">Medium Flow (Yellow)</option>
                <option value="high">High Congestion (Orange)</option>
                <option value="critical">Critical Anomaly (Red)</option>
              </select>
            </div>

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ width: '100%', marginTop: 'auto', padding: '0.8rem' }}
              disabled={isSubmitting}
            >
              {isSubmitting ? "Ingesting data stream..." : "Inject Telemetry Metrics"}
            </button>
            
            {telemetryMessage && (
              <div role="alert" aria-live="assertive" style={{ 
                padding: '0.85rem', 
                background: telemetryMessage.includes('🚨') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(6, 182, 212, 0.08)', 
                border: `1px solid ${telemetryMessage.includes('🚨') ? 'var(--danger)' : 'var(--accent-cyan)'}`, 
                borderRadius: 'var(--radius-sm)', 
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <Radio size={14} className="pulse-card" />
                <span>{telemetryMessage}</span>
              </div>
            )}
          </form>
        </section>

        {/* Live Incident Stream */}
        <section className="card" style={{ display: 'flex', flexDirection: 'column', height: '540px' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
              <AlertOctagon style={{ color: 'var(--danger)' }} size={20} />
              <span>Real-Time Incident Stream</span>
            </span>
            <button 
              onClick={fetchAlerts} 
              className="btn btn-secondary" 
              style={{ padding: '6px 12px', fontSize: '0.75rem', height: 'auto' }} 
              aria-label="Refresh alerts"
            >
              <RefreshCw size={14} />
            </button>
          </h2>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {alerts.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic', padding: '2rem', textAlign: 'center' }}>No active incident reports at this moment.</p>
            ) : (
              alerts.map(alert => (
                <div 
                  key={alert.id}
                  onClick={() => setSelectedAlert(alert)}
                  style={{
                    background: selectedAlert?.id === alert.id ? 'var(--bg-hover)' : 'rgba(255,255,255,0.02)',
                    border: `1px solid ${alert.severity === 'critical' ? 'var(--danger)' : selectedAlert?.id === alert.id ? 'var(--accent-cyan)' : 'var(--glass-border)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.85rem',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 'bold', color: alert.severity === 'critical' ? 'var(--danger)' : 'var(--text-main)', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {alert.severity === 'critical' && <AlertOctagon size={14} />}
                      {alert.title}
                    </span>
                    <span style={{ 
                      fontSize: '0.65rem', 
                      background: alert.status === 'pending' ? 'var(--warning)' : 'var(--success)', 
                      color: 'var(--text-inverse)', 
                      padding: '2px 6px', 
                      borderRadius: '4px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}>
                      {alert.status}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '8px', lineHeight: 1.4 }}>
                    {alert.description}
                  </p>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: 'var(--accent-cyan)', fontWeight: 500, alignItems: 'center' }}>
                    <MapPin size={12} />
                    <span>{alert.location}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                      <Clock size={12} /> {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {/* Suggested dispatch view */}
      {selectedAlert && (
        <section className="card fade-in" style={{ marginTop: '2rem', border: '1px solid var(--accent-cyan)', background: 'rgba(6, 182, 212, 0.02)' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
            <Navigation style={{ color: 'var(--accent-cyan)' }} size={20} />
            <span>Intelligent Dispatch Suggester</span>
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem', alignItems: 'start' }}>
            <div style={{ background: 'var(--bg-secondary)', padding: '1.25rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--glass-border)' }}>
              <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.85rem', textTransform: 'uppercase', fontWeight: 600 }}>Incident Target</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                <div><strong>Incident:</strong> {selectedAlert.title}</div>
                <div><strong>Location:</strong> {selectedAlert.location}</div>
                <div><strong>Details:</strong> {selectedAlert.description}</div>
                <div><strong>Severity:</strong> <span style={{ color: 'var(--danger)', fontWeight: 'bold' }}>{selectedAlert.severity.toUpperCase()}</span></div>
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.85rem', textTransform: 'uppercase', fontWeight: 600 }}>Available Field Volunteers</h3>
              {suggestLoading ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <RefreshCw size={24} className="pulse-card" style={{ animation: 'spin 1s linear infinite' }} />
                  <p style={{ marginTop: '8px' }}>Computing spatial coordinates and language vectors...</p>
                </div>
              ) : suggestions.length === 0 ? (
                <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', color: 'var(--text-muted)' }}>
                  No available field volunteers found in range.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {suggestions.map(sug => (
                    <div 
                      key={sug.staff_id}
                      style={{
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--glass-border)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '1rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 'bold', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <User size={16} style={{ color: 'var(--accent-purple)' }} />
                          {sug.full_name}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', gap: '12px', marginTop: '6px' }}>
                          <span>Distance: {sug.distance_meters}m</span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Languages size={12} /> Speaks: {sug.languages.join(', ').toUpperCase()}
                          </span>
                        </div>
                      </div>

                      <button 
                        onClick={() => handleDispatch(sug.staff_id)}
                        className="btn btn-primary"
                        style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
                      >
                        Dispatch Volunteer
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </main>
  );
});
export default AdminCockpit;
