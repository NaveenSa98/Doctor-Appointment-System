import logoUrl from '../../logo/Logo.jpeg';

function Tick() {
  return (
    <span className="tick" aria-hidden="true">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 12l5 5 9-10" />
      </svg>
    </span>
  );
}

/** Two-panel layout shared by the sign-in and sign-up pages: brand panel + the form. */
export default function AuthShell({ headline, text, points, children }) {
  return (
    <div className="signin">
      <div className="signin-shell">
        <aside className="signin-aside">
          <img src={logoUrl} alt="DocEase" />
          <div>
            <h2>{headline}</h2>
            <p>{text}</p>
          </div>
          <ul className="signin-points">
            {points.map((point) => (
              <li key={point}>
                <Tick />
                {point}
              </li>
            ))}
          </ul>
        </aside>
        {children}
      </div>
    </div>
  );
}
