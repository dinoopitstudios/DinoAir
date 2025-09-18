import { useState, type ReactNode } from 'react';

interface TableProps {
  columns: string[];
  rows: (string | number | ReactNode)[][];
}

export default function Table({ columns, rows }: TableProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  return (
    <div style={{ overflowX: 'auto' }}>
      <div
        style={{
          border: '1px solid #1f2937',
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <table
          className='table'
          style={{
            width: '100%',
            borderCollapse: 'separate',
            borderSpacing: 0,
            color: '#e5e7eb',
            minWidth: 480,
          }}
        >
          <thead>
            <tr style={{ background: '#0f172a' }}>
              {columns.map(col => (
                <th
                  key={col}
                  style={{
                    textAlign: 'left',
                    padding: '10px 12px',
                    fontSize: 13,
                    fontWeight: 700,
                    borderBottom: '1px solid #1f2937',
                    color: '#cbd5e1',
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ padding: 16, color: '#9ca3af', textAlign: 'center' }}
                >
                  No data
                </td>
              </tr>
            ) : (
              rows.map((row, i) => {
                const zebra = i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)';
                const bg = hoverIndex === i ? 'rgba(255,255,255,0.04)' : zebra;
                return (
                  <tr
                    key={i}
                    onMouseEnter={() => setHoverIndex(i)}
                    onMouseLeave={() => setHoverIndex(null)}
                    style={{ background: bg }}
                  >
                    {row.map((cell, j) => (
                      <td
                        key={j}
                        style={{
                          padding: '10px 12px',
                          fontSize: 13,
                          borderBottom: '1px solid #1f2937',
                        }}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
