/**
 * Body for POST /appointments. `status` is only sent for signed-in staff,
 * because the API rejects anything but "scheduled" from anonymous visitors.
 */
export function toCreatePayload(values, { includeStatus }) {
  const body = {
    patient_name: values.patient_name.trim(),
    doctor_id: values.doctor_id,
    hospital_id: values.hospital_id,
    start_time: values.start_time,
    appointment_type: values.appointment_type,
  };
  if (includeStatus) body.status = values.status;
  return body;
}

/** Body for PATCH /appointments/{id}: only the fields that differ from `appointment`. */
export function toPatchPayload(values, appointment) {
  const current = {
    patient_name: appointment.patient_name,
    doctor_id: appointment.doctor.id,
    hospital_id: appointment.hospital.id,
    start_time: appointment.start_time,
    appointment_type: appointment.appointment_type,
    status: appointment.status,
  };
  const next = { ...values, patient_name: values.patient_name.trim() };
  const patch = {};
  for (const key of Object.keys(current)) {
    if (key === 'start_time') {
      if (Date.parse(next.start_time) !== Date.parse(current.start_time)) patch.start_time = next.start_time;
    } else if (next[key] !== current[key]) {
      patch[key] = next[key];
    }
  }
  return patch;
}
