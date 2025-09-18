import { useState, type CSSProperties, type ComponentType, type SVGProps } from 'react';

import { NavLink } from 'react-router-dom';

import ArtifactsPage from '../icons/ArtifactsPage';
import Chat from '../icons/Chat';
import Home from '../icons/Home';
import LocalFileRetrievalAndIndexing from '../icons/LocalFileRetrievalAndIndexing';
import ModelSettingsSystemWatchdog from '../icons/ModelSettingsSystemWatchdog';
import Notes from '../icons/Notes';
import OtherToolsPage from '../icons/OtherToolsPage';
import Projects from '../icons/Projects';
import SettingsPage from '../icons/SettingsPage';

type Item = {
  to: string;
  label: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
};

const items: Item[] = [
  { to: '/', label: 'Home', Icon: Home },
  { to: '/chat', label: 'Chat', Icon: Chat },
  { to: '/projects', label: 'Projects', Icon: Projects },
  { to: '/artifacts', label: 'Artifacts', Icon: ArtifactsPage },
  { to: '/notes', label: 'Notes', Icon: Notes },
  { to: '/tools', label: 'Tools', Icon: OtherToolsPage },
  { to: '/utilities', label: 'Utilities', Icon: OtherToolsPage },
  { to: '/files', label: 'Files', Icon: LocalFileRetrievalAndIndexing },
  { to: '/model-settings', label: 'Model', Icon: ModelSettingsSystemWatchdog },
  { to: '/settings', label: 'Settings', Icon: SettingsPage },
];

const tokens = {
  textBase: '#a3a3a3',
  textHover: '#e5e7eb',
  textActive: '#60a5fa',
  headerBg: '#111827',
  border: '#1f2937',
  focusRing: '#374151',
} as const;

function LinkItem({ to, label, Icon }: Item) {
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);

  return (
    <NavLink
      key={to}
      to={to}
      className={({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={({ isActive }) => {
        const color = isActive ? tokens.textActive : hovered ? tokens.textHover : tokens.textBase;
        return {
          color,
          borderBottom: isActive ? `2px solid ${tokens.textActive}` : '2px solid transparent',
          textDecoration: 'none',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '0 8px',
          height: 56,
          outline: focused ? `2px solid ${tokens.focusRing}` : 'none',
          outlineOffset: 2,
        } as CSSProperties;
      }}
    >
      <Icon width={16} height={16} />
      <span>{label}</span>
    </NavLink>
  );
}

export default function TopNav() {
  return (
    <div
      style={{
        width: '100%',
        background: tokens.headerBg,
        borderBottom: `1px solid ${tokens.border}`,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 56,
          padding: '0 18px',
        }}
      >
        <h1 style={{ margin: 0, fontSize: 18, color: tokens.textHover }}>DinoAir3</h1>
        <nav aria-label='Primary' style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
          {items.map(it => (
            <LinkItem key={it.to} {...it} />
          ))}
        </nav>
      </div>
    </div>
  );
}
