import { Link } from 'react-router-dom';

const STEPS = [
  { title: 'Choose a hospital and doctor', text: 'Only doctors who visit the hospital you pick are listed.' },
  { title: 'Pick a free time', text: 'Taken slots are greyed out, so you never double book.' },
  { title: 'Get your reference number', text: 'Shown straight away. No account needed.' },
];

export default function HomePage() {
  return (
    <div className="container hero">
      <section className="hero-copy">
        <h1>Book your doctor visit in under a minute.</h1>
        <p className="lead">
          Pick a hospital, choose a doctor, and grab a free slot. Times are shown in your local time zone.
        </p>
        <div className="hero-actions">
          <Link to="/book" className="btn btn-primary btn-lg">Book an appointment</Link>
          <Link to="/login" className="btn btn-secondary btn-lg">Staff sign in</Link>
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
