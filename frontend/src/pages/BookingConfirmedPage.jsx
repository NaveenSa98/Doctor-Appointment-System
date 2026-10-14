import { useState } from 'react';
import { Link, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/AuthContext';
import { RECEIPT_MESSAGE, RECEIPT_NOTE, receiptRows } from '../utils/receipt';
import { downloadReceipt } from '../utils/receiptPdf';

/** Confirmation and receipt. Opened directly (no booking in state) it goes to /book. */
export default function BookingConfirmedPage() {
  const appointment = useLocation().state?.appointment;
  const { user } = useAuth();
  const [pdf, setPdf] = useState({ pending: false, error: null });
  if (!appointment) return <Navigate to="/book" replace />;

  async function onDownload() {
    setPdf({ pending: true, error: null });
    try {
      await downloadReceipt(appointment);
      setPdf({ pending: false, error: null });
    } catch {
      setPdf({ pending: false, error: 'Could not create the PDF. Please try again.' });
    }
  }

  return (
    <div className="container narrow">
      <article className="card confirmed receipt" aria-labelledby="receipt-title">
        <span className="confirmed-mark" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12l5 5 9-10" />
          </svg>
        </span>
        <h1 id="receipt-title" className="page-title">You are booked</h1>
        <p className="muted">{RECEIPT_MESSAGE}</p>
        <p className="reference" aria-label="Reference number">
          {appointment.id}
        </p>

        <dl className="summary">
          {receiptRows(appointment).map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>

        <p className="receipt-note">{RECEIPT_NOTE}</p>

        <div className="receipt-actions">
          <button type="button" className="btn btn-primary" onClick={onDownload} disabled={pdf.pending}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 4v11M7 11l5 5 5-5M5 20h14" />
            </svg>
            {pdf.pending ? 'Preparing PDF…' : 'Download receipt (PDF)'}
          </button>
          <Link to="/book" className="btn btn-secondary">
            Book another
          </Link>
          {user?.role === 'patient' && (
            <Link to="/my-bookings" className="btn btn-secondary">
              My bookings
            </Link>
          )}
        </div>
        {pdf.error && (
          <p className="field-error" role="alert">
            {pdf.error}
          </p>
        )}
      </article>
    </div>
  );
}
