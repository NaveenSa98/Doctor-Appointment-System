import { Link } from 'react-router-dom';
import logoUrl from '../../logo/Logo.jpeg';

const ICONS = {
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="M20 20l-4-4" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
    </>
  ),
  ticket: (
    <>
      <path d="M4 8a2 2 0 0 0 0 4v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4a2 2 0 0 1 0-4V6a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1z" />
      <path d="M14 5v12" strokeDasharray="2 3" />
    </>
  ),
  shield: <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z M9 12l2 2 4-4" />,
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" />
    </>
  ),
};

function Icon({ name }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

const STEPS = [
  {
    icon: 'search',
    title: 'Find your doctor',
    text: 'Pick a hospital, then choose from the doctors who visit it.',
  },
  {
    icon: 'clock',
    title: 'Choose a time',
    text: 'See the doctor’s open sessions and tap a free slot. Taken times are greyed out.',
  },
  {
    icon: 'user',
    title: 'Confirm in one step',
    text: 'Add the patient’s name and the kind of visit. No account needed.',
  },
  {
    icon: 'ticket',
    title: 'Keep your reference',
    text: 'You get a reference number straight away. Create a free account to see every booking in one place.',
  },
];

const BENEFITS = [
  { icon: 'clock', title: 'Live availability', text: 'Only open times are shown, always up to date.' },
  { icon: 'shield', title: 'No double bookings', text: 'A slot can only be taken once.' },
  { icon: 'globe', title: 'Times in your zone', text: 'Shown in your local time, wherever you are.' },
];

export default function HomePage() {
  return (
    <>
      <div className="container hero">
        <section className="hero-copy">
          <img className="hero-logo" src={logoUrl} alt="DocEase" />
          <h1>Your Health, Your Time, Our Priority.</h1>
          <p className="lead">
            A user-friendly doctor channelling system that allows patients to search for doctors, check
            availability, book appointments, and manage their reservations online.
          </p>
          <div className="hero-actions">
            <Link to="/book" className="btn btn-primary btn-lg">Book an appointment</Link>
            <Link to="/signup" className="btn btn-secondary btn-lg">Create an account</Link>
          </div>
        </section>

        <section className="card benefits" aria-label="Why DocEase">
          <ul>
            {BENEFITS.map((b) => (
              <li key={b.title}>
                <span className="icon-tile">
                  <Icon name={b.icon} />
                </span>
                <span>
                  <strong>{b.title}</strong>
                  <span className="sub">{b.text}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="how" aria-labelledby="how-it-works">
        <div className="container how-inner">
          <h2 id="how-it-works">How it works</h2>
          <p className="muted how-lede">Four quick steps from “I need a doctor” to a confirmed visit.</p>
          <ol className="how-steps">
            {STEPS.map((s, i) => (
              <li key={s.title} className="how-step">
                <span className="how-num" aria-hidden="true">{i + 1}</span>
                <span className="icon-tile">
                  <Icon name={s.icon} />
                </span>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </li>
            ))}
          </ol>
          <div className="how-cta">
            <Link to="/book" className="btn btn-primary btn-lg">Start booking</Link>
          </div>
        </div>
      </section>
    </>
  );
}
