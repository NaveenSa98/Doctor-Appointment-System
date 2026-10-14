import { TYPES } from '../components/AppointmentForm';
import { STATUS_LABELS } from '../components/StatusBadge';
import { formatFullDateTime } from './datetime';

export const RECEIPT_MESSAGE =
  'Keep this reference number. Staff will ask for it when you visit the doctor or need to make any changes.';

export const RECEIPT_NOTE =
  'Please quote the reference number above when you contact the clinic. Times are shown in your local time zone.';

/** The labelled details shown on the confirmation page and printed in the PDF. */
export function receiptRows(appointment) {
  return [
    ['Patient', appointment.patient_name],
    ['Doctor', `${appointment.doctor.full_name}, ${appointment.doctor.specialty}`],
    ['Hospital', appointment.hospital.name],
    ['Date and time', formatFullDateTime(appointment.start_time)],
    ['Visit type', TYPES[appointment.appointment_type] ?? appointment.appointment_type],
    ['Status', STATUS_LABELS[appointment.status] ?? appointment.status],
    ['Booked on', formatFullDateTime(appointment.created_at)],
  ];
}

/** File name offered for the download, e.g. "DocEase-receipt-3f2a9c1e.pdf". */
export const receiptFileName = (appointmentId) => `DocEase-receipt-${appointmentId.slice(0, 8)}.pdf`;
