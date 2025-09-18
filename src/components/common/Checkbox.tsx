import { useId } from 'react';

interface CheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
}

export default function Checkbox({ checked, onChange, label }: CheckboxProps) {
  const id = useId();

  return (
    <label
      htmlFor={id}
      className='checkbox'
      style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}
    >
      <input
        id={id}
        type='checkbox'
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        style={{
          width: 16,
          height: 16,
          appearance: 'none',
          background: checked ? '#32bc9b' : '#0f3460',
          border: '1px solid #2a3b7a',
          borderRadius: 3,
          outline: 'none',
          display: 'grid',
          placeItems: 'center',
        }}
      />
      {label ? <span style={{ color: '#e6eaff', fontSize: 14 }}>{label}</span> : null}
    </label>
  );
}
