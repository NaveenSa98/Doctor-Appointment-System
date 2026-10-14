import { Link } from 'react-router-dom';

/** Site footer: quick links and an honest note that the data is a demo. */
export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <strong>DocEase</strong>
          <p>Your health, your time, our priority.</p>
        </div>
        <nav aria-label="Footer" className="footer-links">
          <Link to="/book">Find a doctor</Link>
          <Link to="/login">Log in</Link>
          <Link to="/signup">Join DocEase</Link>
        </nav>
        <p className="footer-note">A demonstration system. All people and bookings shown are synthetic.</p>
      </div>
    </footer>
  );
}
