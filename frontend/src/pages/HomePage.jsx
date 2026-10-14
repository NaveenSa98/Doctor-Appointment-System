import { Link } from 'react-router-dom';
import logoUrl from '../../logo/Logo.jpeg';

const STEPS = [
  { title: 'Choose a hospital and doctor', text: 'Only doctors who visit the hospital you pick are listed.' },
  { title: 'Pick a free time', text: 'Taken slots are greyed out, so you never double book.' },
  { title: 'Get your reference number', text: 'Shown straight away. No account needed.' },
];

export default function HomePage() {
  return (
    <div className="container hero">
      <section className="hero-copy">
        <img className="hero-logo" src={logoUrl} alt="DocEase" />
        <h1>Your Health, Your Time, Our Priority.</h1>
        <p className="lead">
          A user-friendly doctor channelling system that allows patients to search for doctors, check availability, book appointments, and manage their reservations online.
        </p>
        <div className="hero-actions">
          <Link to="/book" className="btn btn-primary btn-lg">Book an appointment</Link>
        </div>
      </section>
      <section className="card steps" aria-labelledby="how-it-works">
        <h2 id="how-it-works">How it works</h2>
        <ol>
          {STEPS.map((s) => (
            <li key={s.title}>
              <strong>{s.title}</strong>
              <span>{s.text}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
