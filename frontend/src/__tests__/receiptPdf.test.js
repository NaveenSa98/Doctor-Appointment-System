import { jsPDF } from 'jspdf';
import { makeAppointment } from './mocks/handlers';
import { createReceiptPdf } from '../utils/receiptPdf';
import { receiptFileName, receiptRows } from '../utils/receipt';

const ID = '3f2a9c1e-7b64-4d0a-9c11-5e8f2a6b7d90';
const base = {
  id: ID,
  patient_name: 'Jane Perera',
  appointment_type: 'check_up',
  start_time: '2099-01-05T15:00:00Z',
  created_at: '2098-12-20T08:15:00Z',
};

// `compress: false` keeps the page text readable in the output so it can be searched.
const build = (overrides = {}) =>
  createReceiptPdf(jsPDF, makeAppointment(1, { ...base, ...overrides }), {
    compress: false,
    issuedAt: new Date('2099-01-06T04:00:00Z'),
  });

describe('receipt PDF', () => {
  it('is a valid single A4 page', () => {
    const doc = build();
    expect(doc.output()).toMatch(/^%PDF-1\.\d/);
    expect(doc.getNumberOfPages()).toBe(1);
    const { width, height } = doc.internal.pageSize;
    expect([Math.round(width), Math.round(height)]).toEqual([210, 297]);
  });

  it('contains the reference, every detail and the guidance text', () => {
    const text = build().output();
    for (const expected of [
      'DocEase',
      'Appointment receipt',
      'Appointment confirmed',
      'REFERENCE NUMBER',
      ID,
      'Jane Perera',
      'Dr. Amara Silva, Cardiology',
      'Riverside General',
      'Check-up',
      'Scheduled',
      'Keep this reference number.',
      'any changes.',
    ]) {
      expect(text).toContain(expected);
    }
    for (const [label] of receiptRows(makeAppointment(1, base))) {
      expect(text).toContain(label);
    }
  });

  it('stays on one page when a value is very long', () => {
    const long = 'The Royal Colombo Teaching and Research Hospital of Medical Sciences '.repeat(4).trim();
    const doc = createReceiptPdf(jsPDF, makeAppointment(1, { ...base, hospital: { id: 'h9', name: long } }), {
      compress: false,
    });
    expect(doc.getNumberOfPages()).toBe(1);
  });

  it('turns typographic punctuation into plain characters the PDF fonts can draw', () => {
    const text = build({ patient_name: 'Nimal D’Souza – Jr.' }).output();
    expect(text).toContain("Nimal D'Souza - Jr.");
  });

  it('does not fail on names in other scripts when no canvas is available', () => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = () => null;
    try {
      const doc = build({ patient_name: 'ජේන් පෙරේරා' });
      expect(doc.getNumberOfPages()).toBe(1);
      expect(doc.output()).toContain(ID);
    } finally {
      HTMLCanvasElement.prototype.getContext = original;
    }
  });

  it('names the file after the start of the reference', () => {
    expect(receiptFileName(ID)).toBe('DocEase-receipt-3f2a9c1e.pdf');
  });
});
