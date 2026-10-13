const STATUS = {
  scheduled: { label: 'Scheduled', icon: <circle cx="12" cy="12" r="8" /> },
  confirmed: { label: 'Confirmed', icon: <path d="M5 12l5 5 9-10" /> },
  completed: { label: 'Completed', icon: <path d="M4 12h16M12 4v16" transform="rotate(45 12 12)" /> },
  cancelled: { label: 'Cancelled', icon: <path d="M6 6l12 12M18 6L6 18" /> },
  no_show: { label: 'No show', icon: <path d="M5 12h14" /> },
};

/** Status as text plus an icon, never colour alone. */
export default function StatusBadge({ status }) {
  const { label, icon } = STATUS[status] ?? { label: status, icon: null };
  return (
    <span className={`badge badge-${status}`}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {icon}
      </svg>
      {label}
    </span>
  );
}

export const STATUS_LABELS = Object.fromEntries(Object.entries(STATUS).map(([k, v]) => [k, v.label]));
