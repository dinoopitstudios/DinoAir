import type { CSSProperties, InputHTMLAttributes } from 'react';

interface SearchInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'type' | 'value'> {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function SearchInput({
  value,
  onChange,
  placeholder,
  className = 'search-input',
  style,
  ...restProps
}: SearchInputProps) {
  const responsiveStyle: CSSProperties = {
    background: '#0f3460',
    border: '1px solid #2a3b7a',
    borderRadius: 6,
    color: '#e6eaff',
    padding: '8px 10px',
    fontSize: 14,
    width: '100%',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    ...style,
  };

  return (
    <input
      className={className}
      type='text'
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder ?? 'Search...'}
      style={responsiveStyle}
      aria-label={restProps['aria-label'] || placeholder || 'Search input'}
      {...restProps}
    />
  );
}
