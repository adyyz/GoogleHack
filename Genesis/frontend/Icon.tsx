const paths = {
  cases: 'M8 3h8v4H8z M7 5H4v16h16V5h-3 M8 12h8 M8 16h5',
  alerts: 'M12 3L2 21h20z M12 9v5 M12 17v1',
  analyst: 'M15 7a3 3 0 1 1-6 0 3 3 0 0 1 6 0z M4 21v-2a6 6 0 0 1 12 0v2 M17 12l2 2 3-4',
  investigations: 'M4 4h6v7H4z M14 4h6v4h-6z M14 12h6v8h-6z M4 15h6v5H4z',
  evolution: 'M4 17l6-6 4 3 6-9 M14 5h6v6',
  system: 'M8 4h8v5H8z M3 16h6v5H3z M15 16h6v5h-6z M12 9v4 M6 16v-3h12v3',
  search: 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13z M16 16l5 5',
  arrow: 'M5 12h14 M13 6l6 6-6 6',
  shield: 'M12 3l8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6z M8 12l3 3 5-6',
  info: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z M12 10v6 M12 6v1',
  close: 'M6 6l12 12 M18 6L6 18',
  check: 'M5 12l4 4L19 6',
  lock: 'M6 10h12v11H6z M8 10V7a4 4 0 0 1 8 0v3',
  logo: 'M4 9V4h5 M15 4h5v5 M20 15v5h-5 M9 20H4v-5 M8 14l4-6 4 6 M10 12h4',
};

export function Icon({ name, size = 18 }: { name: keyof typeof paths; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}
