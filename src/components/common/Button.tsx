import { useState, type ButtonHTMLAttributes, type CSSProperties, type ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

export default function Button({
  children,
  variant = 'primary',
  disabled,
  style,
  ...rest
}: ButtonProps) {
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);

  const base: CSSProperties = {
    height: 38,
    padding: '0 14px',
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 500,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all 0.15s ease',
    outline: focused ? '2px solid #60a5fa' : 'none',
    outlineOffset: 2,
    border: '1px solid transparent',
    background: 'transparent',
    color: '#e5e7eb',
  };

  const variants: Record<ButtonVariant, CSSProperties> = {
    primary: {
      background: hovered ? '#1d4ed8' : '#2563eb',
      color: '#ffffff',
    },
    secondary: {
      background: hovered ? '#4b5563' : '#374151',
      color: '#e5e7eb',
    },
    ghost: {
      background: hovered ? 'rgba(255,255,255,0.06)' : 'transparent',
      color: '#e5e7eb',
    },
  };

  return (
    <button
      className='btn'
      disabled={disabled}
      onMouseEnter={() => !disabled && setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={{ ...base, ...variants[variant], ...style }}
      {...rest}
    >
      {children}
    </button>
  );
}
