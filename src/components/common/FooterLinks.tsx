import { useState, type FC, type ReactNode } from 'react';

export default function FooterLinks() {
  const base = '#9ca3af';
  const hover = '#e5e7eb';

  const LinkItem: FC<{ href: string; children: ReactNode }> = ({ href, children }) => {
    const [h, setH] = useState(false);
    return (
      <a
        href={href}
        onMouseEnter={() => setH(true)}
        onMouseLeave={() => setH(false)}
        style={{
          color: h ? hover : base,
          textDecoration: 'none',
          fontSize: 13,
        }}
      >
        {children}
      </a>
    );
  };

  return (
    <div
      style={{
        display: 'flex',
        gap: 14,
        alignItems: 'center',
        flexWrap: 'wrap',
      }}
    >
      <LinkItem href='#'>Privacy Policy</LinkItem>
      <span aria-hidden='true' style={{ opacity: 0.5 }}>
        •
      </span>
      <LinkItem href='#'>Terms of Service</LinkItem>
      <span aria-hidden='true' style={{ opacity: 0.5 }}>
        •
      </span>
      <LinkItem href='#'>Contact Us</LinkItem>
    </div>
  );
}
