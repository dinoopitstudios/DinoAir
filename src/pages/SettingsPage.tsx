import { useCallback, useEffect, useState } from 'react';

import { LiveRegion } from '../components/accessibility/LiveRegion';
import Banner from '../components/common/Banner';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Checkbox from '../components/common/Checkbox';
import Toggle from '../components/common/Toggle';
import SettingsIcon from '../components/icons/SettingsPage';
import PageContainer from '../components/layout/PageContainer';
import PageHeader from '../components/layout/PageHeader';
import { useAnnouncement } from '../hooks/useAnnouncement';
import { useResponsive } from '../hooks/useResponsive';
import { API_BASE_URL, getCapabilities, getConfigDirs, getMetrics, getVersion } from '../lib/api';

/**
 * SettingsPage component renders the settings page allowing users to configure
 * general, advanced, and LM Studio settings.
 *
 * @returns JSX.Element - The settings page UI.
 */
export default function SettingsPage() {
  const { isMobile } = useResponsive();
  const { announceSuccess, announceError, announceInfo } = useAnnouncement();

  // General Settings
  const [darkMode, setDarkMode] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [autoSave, setAutoSave] = useState(false);

  // Advanced Settings
  const [advancedEnabled, setAdvancedEnabled] = useState(false);
  const [betaFeatures, setBetaFeatures] = useState(false);
  const [telemetry, setTelemetry] = useState(true);

  // Save state
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Backend integration
  const [backendLoading, setBackendLoading] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  type VersionInfo = { version?: string; build?: string; commit?: string };
  const [ver, setVer] = useState<VersionInfo | null>(null);
  const [caps, setCaps] = useState<string[]>([]);
  const [uptimeSeconds, setUptimeSeconds] = useState<number>(0);

  // LM Studio Settings
  const [lmStudioUrl, setLmStudioUrl] = useState('http://127.0.0.1:1234');
  const [lmStudioModel, setLmStudioModel] = useState('llama-3.1-8b-instruct');
  const [lmStudioEnabled, setLmStudioEnabled] = useState(true);
  const [lmStudioTesting, setLmStudioTesting] = useState(false);
  const [lmStudioStatus, setLmStudioStatus] = useState<'connected' | 'disconnected' | 'unknown'>(
    'unknown'
  );

  const loadBackendInfo = useCallback(async () => {
    setBackendLoading(true);
    setBackendError(null);
    announceInfo('Loading backend information...');
    try {
      const [v, c, m, d] = await Promise.all([
        getVersion(),
        getCapabilities().then(x => (Array.isArray(x?.capabilities) ? x.capabilities : [])),
        getMetrics(),
        getConfigDirs(),
      ]);
      // Version info (optionally includes commit)
      setVer({
        version: v?.version,
        build: v?.build,
        commit: (v as { commit?: string })?.commit,
      });
      setCaps(c);
      // Extract uptimeSeconds if available from nested metrics
      const uptimeVal = (m as { metrics?: { uptimeSeconds?: number } })?.metrics?.uptimeSeconds;
      const u = typeof uptimeVal === 'number' ? uptimeVal : 0;
      setUptimeSeconds(u);
      void d; // fetched for potential future use
      announceSuccess('Backend information loaded successfully');
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      setBackendError(errorMsg);
      announceError(`Failed to load backend information: ${errorMsg}`);
    } finally {
      setBackendLoading(false);
    }
  }, [announceError, announceInfo, announceSuccess]);

  useEffect(() => {
    void loadBackendInfo();
  }, [loadBackendInfo]);

  /**
   * Initiates the save process for settings by displaying a saving indicator,
   * announcing success upon completion, and resetting indicators after a delay.
   */
  function saveChanges() {
    setSaving(true);
    setSaved(false);
    announceInfo('Saving settings...');
    setTimeout(() => {
      setSaving(false);
      setSaved(true);
      announceSuccess('Settings saved successfully');
      setTimeout(() => setSaved(false), 1200);
    }, 600);
  }

  return (
    <PageContainer className='settings-page'>
      <PageHeader icon={<SettingsIcon width={20} height={20} />} title='Settings' />

      <main role='main' aria-label='Settings configuration'>
        {saved ? (
          <div style={{ marginBottom: 10 }} role='alert' aria-live='polite'>
            <Banner type='success'>Settings saved.</Banner>
          </div>
        ) : null}

        <section style={{ margin: '12px 0' }}>
      const handleLmStudioUrlChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setLmStudioUrl(e.target.value);
      }, []);

      const handleLmStudioModelChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setLmStudioModel(e.target.value);
      }, []);

      const handleTestLMStudioConnection = useCallback(async () => {
        setLmStudioTesting(true);
        try {
          const response = await fetch(`${lmStudioUrl}/v1/models`);
          if (response.ok) {
            setLmStudioStatus('connected');
            announceSuccess('LM Studio connection successful!');
          } else {
            setLmStudioStatus('disconnected');
            announceError('LM Studio connection failed');
          }
        } catch (error) {
          setLmStudioStatus('disconnected');
          announceError('Unable to connect to LM Studio');
        } finally {
          setLmStudioTesting(false);
        }
      }, [lmStudioUrl, announceSuccess, announceError]);

      const handleDarkModeToggle = useCallback((value: boolean) => {
        setDarkMode(value);
        announceInfo(`Dark mode ${value ? 'enabled' : 'disabled'}`);
      }, [announceInfo]);

      const handleNotificationsToggle = useCallback((value: boolean) => {
        setNotifications(value);
        announceInfo(`Notifications ${value ? 'enabled' : 'disabled'}`);
      }, [announceInfo]);

      const handleAutoSaveToggle = useCallback((value: boolean) => {
        setAutoSave(value);
        announceInfo(`Auto-save ${value ? 'enabled' : 'disabled'}`);
      }, [announceInfo]);

      <Card title='Backend Integration'>
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ color: '#9ca3af' }}>API Base:</span>
            <code>{API_BASE_URL}</code>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <div>
              Version: <strong>{ver?.version ?? '—'}</strong>
            </div>
            <div>
              Build: <code>{ver?.build ?? '—'}</code>
            </div>
            <div>
              Commit: <code>{ver?.commit ?? '—'}</code>
            </div>
            <div>
              Uptime: <strong>{uptimeSeconds}s</strong>
            </div>
            <div>
              Capabilities: <strong>{caps.length}</strong>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Button
              variant='secondary'
              onClick={loadBackendInfo}
              disabled={backendLoading}
              data-testid='refresh-backend-button'
              aria-label='Refresh backend information'
            >
              {backendLoading ? 'Refreshing…' : 'Refresh Backend Info'}
            </Button>
            {backendError ? <span style={{ color: '#fca5a5' }}>{backendError}</span> : null}
          </div>
        </div>
      </Card>
    </section>

    <section>
      <Card title='LM Studio Configuration'>
        <div style={{ display: 'grid', gap: 10 }}>
          <div>
            <label htmlFor='lmstudio-url' style={{ display: 'block', marginBottom: 4 }}>
              LM Studio URL:
            </label>
            <input
              id='lmstudio-url'
              type='text'
              value={lmStudioUrl}
              onChange={handleLmStudioUrlChange}
              placeholder='http://127.0.0.1:1234'
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #374151',
                borderRadius: '4px',
                backgroundColor: '#1f2937',
                color: '#f9fafb',
              }}
            />
          </div>

          <div>
            <label htmlFor='lmstudio-model' style={{ display: 'block', marginBottom: 4 }}>
              Model Name:
            </label>
            <input
              id='lmstudio-model'
              type='text'
              value={lmStudioModel}
              onChange={handleLmStudioModelChange}
              placeholder='llama-3.1-8b-instruct'
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #374151',
                borderRadius: '4px',
                backgroundColor: '#1f2937',
                color: '#f9fafb',
              }}
            />
          </div>

          <Toggle
            checked={lmStudioEnabled}
            onChange={setLmStudioEnabled}
            label='Enable LM Studio Integration'
          />
          <p style={{ fontSize: '0.875rem', color: '#9ca3af', marginTop: '-8px' }}>
            Connect to local LM Studio instance for AI responses
          </p>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Button
              variant='secondary'
              onClick={handleTestLMStudioConnection}
              disabled={lmStudioTesting}
              data-testid='test-lmstudio-button'
            >
              {lmStudioTesting ? 'Testing...' : 'Test Connection'}
            </Button>

            <div
              style={{
                padding: '4px 8px',
                borderRadius: '4px',
                backgroundColor:
                  lmStudioStatus === 'connected'
                    ? '#059669'
                    : lmStudioStatus === 'disconnected'
                      ? '#dc2626'
                      : '#6b7280',
                color: 'white',
                fontSize: '0.875rem',
              }}
            >
              {lmStudioStatus === 'connected'
                ? '● Connected'
                : lmStudioStatus === 'disconnected'
                  ? '● Disconnected'
                  : '● Unknown'}
            </div>
          </div>
        </div>
      </Card>
    </section>

    <section
      style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
        gap: 12,
      }}
    >
      <Card title='General Settings'>
        <div
          style={{ display: 'grid', gap: 10 }}
          role='group'
          aria-labelledby='general-settings'
        >
          <h3 id='general-settings' className='sr-only'>
            General Settings
          </h3>
          <Toggle
            checked={darkMode}
            onChange={handleDarkModeToggle}
            label='Enable Dark Mode'
            data-testid='dark-mode-toggle'
            aria-label='Enable dark mode'
          />
          <Toggle
            checked={notifications}
            onChange={handleNotificationsToggle}
            label='Enable Notifications'
            data-testid='notifications-toggle'
            aria-label='Enable notifications'
          />
          <Toggle
            checked={autoSave}
            onChange={handleAutoSaveToggle}
            label='Auto-save Changes'
            data-testid='auto-save-toggle'
            aria-label='Enable auto-save'
          />
        </div>
      </Card>

      <Card title='Advanced Settings'>
        <div
          style={{ display: 'grid', gap: 10 }}
          role='group'
          aria-labelledby='advanced-settings'
        >
          <h3 id='advanced-settings' className='sr-only'>
            Advanced Settings
          </h3>
          <Toggle
            checked={advancedEnabled}
            onChange={setAdvancedEnabled}
            label='Enable Advanced Mode'
            data-testid='advanced-mode-toggle'
            aria-label='Enable advanced mode'
          />
          <Checkbox
            checked={betaFeatures}
            onChange={setBetaFeatures}
            label='Enable experimental features'
            data-testid='beta-features-checkbox'
            aria-label='Enable experimental features'
          />
          <Checkbox
            checked={telemetry}
            onChange={setTelemetry}
            label='Send anonymous telemetry'
            data-testid='telemetry-checkbox'
            aria-label='Send anonymous telemetry'
          />
        </div>
      </Card>
    </section>

    <div style={{ marginTop: 12 }}>
      <Button
        variant='primary'
        onClick={saveChanges}
        disabled={saving}
        data-testid='save-settings-button'
        aria-label='Save settings'
        style={{
          minWidth: isMobile ? '100%' : 'auto',
        }}
      >
        {saving ? 'Saving…' : 'Save Changes'}
      </Button>
    </div>
  </main>

  {/* Screen reader live region for announcements */}
  <LiveRegion ariaLabel='Settings page announcements' showLatestOnly />
</PageContainer>
