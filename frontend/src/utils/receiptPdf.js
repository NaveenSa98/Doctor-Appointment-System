import logoUrl from '../../logo/Logo.jpeg';
import { formatFullDateTime } from './datetime';
import { RECEIPT_MESSAGE, RECEIPT_NOTE, receiptFileName, receiptRows } from './receipt';

// A4 portrait, in millimetres.
const PAGE_W = 210;
const PAGE_H = 297;
const MARGIN = 18;
const CONTENT_W = PAGE_W - MARGIN * 2;

const TEAL = [11, 122, 117];
const INK = [14, 31, 30];
const MUTED = [90, 111, 109];
const LINE = [220, 230, 228];
const SOFT = [244, 247, 246];

const MM_PER_PT = 25.4 / 72;
const CANVAS_SCALE = 4; // canvas pixels per point (about 290 dpi) for text jsPDF cannot encode
const CANVAS_FONT = 'system-ui, "Segoe UI", "Noto Sans", sans-serif';

// jsPDF's built-in fonts cover Latin-1. Anything else (Sinhala, Tamil, ...) is drawn as an image.
const LATIN1 = /^[\x20-\x7e\xa0-\xff]*$/;
const PUNCTUATION = { '‘': "'", '’': "'", '“': '"', '”': '"', '–': '-', '—': '-', '…': '...' };
const normalize = (text) => text.replace(/[‘’“”–—…]/g, (c) => PUNCTUATION[c]);

/** Draws text with jsPDF, falling back to a canvas image for characters its fonts lack. */
function createWriter(doc) {
  let ctx = null;
  let triedCanvas = false;

  function canvasContext() {
    if (!triedCanvas) {
      triedCanvas = true;
      try {
        ctx = document.createElement('canvas').getContext('2d');
      } catch {
        ctx = null;
      }
    }
    return ctx;
  }

  /** The text to use and whether jsPDF can draw it natively. */
  function prepare(text) {
    const clean = normalize(String(text));
    if (LATIN1.test(clean)) return { text: clean, native: true };
    if (canvasContext()) return { text: clean, native: false };
    return { text: clean.replace(/[^\x20-\x7e\xa0-\xff]/g, '?'), native: true };
  }

  function setNativeFont({ size, bold, font = 'helvetica' }) {
    doc.setFont(font, bold ? 'bold' : 'normal');
    doc.setFontSize(size);
  }

  function setCanvasFont({ size, bold }) {
    ctx.font = `${bold ? 700 : 400} ${size * CANVAS_SCALE}px ${CANVAS_FONT}`;
  }

  function width(text, opts) {
    const p = prepare(text);
    if (p.native) {
      setNativeFont(opts);
      return doc.getTextWidth(p.text);
    }
    setCanvasFont(opts);
    return (ctx.measureText(p.text).width / CANVAS_SCALE) * MM_PER_PT;
  }

  /** Break text into lines no wider than maxWidth (mm), at spaces. */
  function wrap(text, maxWidth, opts) {
    const lines = [];
    let current = '';
    for (const word of String(text).split(/\s+/).filter(Boolean)) {
      const candidate = current ? `${current} ${word}` : word;
      if (current && width(candidate, opts) > maxWidth) {
        lines.push(current);
        current = word;
      } else {
        current = candidate;
      }
    }
    if (current) lines.push(current);
    return lines.length ? lines : [''];
  }

  /** Draw one line with its baseline at y. */
  function draw(text, x, y, opts) {
    const { color = INK, align = 'left' } = opts;
    const p = prepare(text);
    const w = width(text, opts);
    const left = align === 'right' ? x - w : x;
    if (p.native) {
      setNativeFont(opts);
      doc.setTextColor(...color);
      doc.text(p.text, left, y);
      return;
    }
    const canvas = ctx.canvas;
    setCanvasFont(opts);
    const widthPx = Math.ceil(ctx.measureText(p.text).width) + 4;
    const heightPx = Math.ceil(opts.size * 1.5 * CANVAS_SCALE);
    const baselinePx = opts.size * 1.15 * CANVAS_SCALE;
    canvas.width = widthPx; // resizing clears the canvas and resets the font
    canvas.height = heightPx;
    setCanvasFont(opts);
    ctx.fillStyle = `rgb(${color.join(',')})`;
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(p.text, 0, baselinePx);
    doc.addImage(
      canvas.toDataURL('image/png'),
      'PNG',
      left,
      y - (baselinePx / CANVAS_SCALE) * MM_PER_PT,
      (widthPx / CANVAS_SCALE) * MM_PER_PT,
      (heightPx / CANVAS_SCALE) * MM_PER_PT,
    );
  }

  /** Draw wrapped text; returns the y just below the last line. */
  function block(text, x, y, maxWidth, opts, lineHeight) {
    let cursor = y;
    for (const line of wrap(text, maxWidth, opts)) {
      draw(line, x, cursor, opts);
      cursor += lineHeight;
    }
    return cursor;
  }

  return { draw, block, wrap, width };
}

/**
 * Lay out the receipt on one A4 page.
 * @param {new (options: object) => import('jspdf').jsPDF} JsPDF the jsPDF constructor
 * @param {object} appointment an API appointment
 * @param {{ logo?: CanvasImageSource | null, issuedAt?: Date, compress?: boolean }} [options]
 */
export function createReceiptPdf(JsPDF, appointment, { logo = null, issuedAt = new Date(), compress = true } = {}) {
  const doc = new JsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait', compress });
  doc.setProperties({
    title: `DocEase appointment receipt ${appointment.id}`,
    subject: 'Appointment receipt',
    author: 'DocEase',
  });
  const write = createWriter(doc);

  // Header: logo, name, and when the receipt was issued.
  if (logo) doc.addImage(logo, 'JPEG', MARGIN, 14, 16, 16);
  const textX = logo ? MARGIN + 20 : MARGIN;
  write.draw('DocEase', textX, 22, { size: 18, bold: true, color: INK });
  write.draw('Appointment receipt', textX, 28, { size: 10, color: MUTED });
  write.draw('Issued', PAGE_W - MARGIN, 20, { size: 8, color: MUTED, align: 'right' });
  write.draw(formatFullDateTime(issuedAt.toISOString()), PAGE_W - MARGIN, 25, {
    size: 9,
    bold: true,
    color: INK,
    align: 'right',
  });
  doc.setDrawColor(...TEAL);
  doc.setLineWidth(0.8);
  doc.line(MARGIN, 36, PAGE_W - MARGIN, 36);

  // Title with a tick badge.
  doc.setFillColor(...TEAL);
  doc.circle(MARGIN + 4.5, 50.5, 4.5, 'F');
  doc.setDrawColor(255, 255, 255);
  doc.setLineWidth(0.9);
  doc.lines([[2, 2], [3.6, -4]], MARGIN + 2.4, 50.8, [1, 1], 'S');
  write.draw('Appointment confirmed', MARGIN + 13, 53, { size: 21, bold: true, color: INK });

  let y = write.block(RECEIPT_MESSAGE, MARGIN, 64, CONTENT_W, { size: 10.5, color: MUTED }, 5.4);

  // Reference box.
  y += 4;
  doc.setFillColor(...SOFT);
  doc.setDrawColor(...LINE);
  doc.setLineWidth(0.4);
  doc.roundedRect(MARGIN, y, CONTENT_W, 25, 3, 3, 'FD');
  write.draw('REFERENCE NUMBER', MARGIN + 7, y + 8, { size: 8, bold: true, color: MUTED });
  write.draw(appointment.id, MARGIN + 7, y + 18, { size: 14, bold: true, color: TEAL, font: 'courier' });
  y += 25 + 12;

  // Details table.
  write.draw('Visit details', MARGIN, y, { size: 12, bold: true, color: INK });
  y += 4;
  doc.setDrawColor(...LINE);
  doc.setLineWidth(0.3);
  doc.line(MARGIN, y, PAGE_W - MARGIN, y);
  const labelW = 44;
  const valueX = MARGIN + labelW;
  const valueW = CONTENT_W - labelW;
  for (const [label, value] of receiptRows(appointment)) {
    const baseline = y + 7;
    write.draw(label, MARGIN, baseline, { size: 9.5, color: MUTED });
    const bottom = write.block(value, valueX, baseline, valueW, { size: 11, bold: true, color: INK }, 5.4);
    y = Math.max(bottom - 5.4, baseline) + 4.5;
    doc.setDrawColor(...LINE);
    doc.line(MARGIN, y, PAGE_W - MARGIN, y);
  }

  write.block(RECEIPT_NOTE, MARGIN, y + 10, CONTENT_W, { size: 9, color: MUTED }, 4.6);

  // Footer.
  doc.setDrawColor(...LINE);
  doc.setLineWidth(0.3);
  doc.line(MARGIN, PAGE_H - 20, PAGE_W - MARGIN, PAGE_H - 20);
  write.draw('DocEase  ·  Your health, your time, our priority.', MARGIN, PAGE_H - 13.5, {
    size: 8.5,
    color: MUTED,
  });
  write.draw('A demonstration system. All people and bookings shown are synthetic.', MARGIN, PAGE_H - 9, {
    size: 8,
    color: MUTED,
  });

  return doc;
}

function loadLogo() {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => resolve(null); // a missing logo must not stop the receipt
    image.src = logoUrl;
  });
}

/** Build the receipt PDF and save it as `DocEase-receipt-<reference>.pdf`. */
export async function downloadReceipt(appointment) {
  // Loaded on demand so the PDF library stays out of the main bundle.
  const [{ jsPDF }, logo] = await Promise.all([import('jspdf'), loadLogo()]);
  createReceiptPdf(jsPDF, appointment, { logo }).save(receiptFileName(appointment.id));
}
