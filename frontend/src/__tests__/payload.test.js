import { toCreatePayload, toPatchPayload } from '../utils/appointmentPayload';
import { fieldErrors } from '../utils/errors';
import { makeAppointment } from './mocks/handlers';

const values = {
  patient_name: '  Jane Perera ',
  doctor_id: 'd1',
  hospital_id: 'h1',
  start_time: '2099-01-05T15:00:00.000Z',
  appointment_type: 'check_up',
  status: 'confirmed',
};

describe('appointment payloads', () => {
  it('trims the name and only includes status for signed-in staff', () => {
    expect(toCreatePayload(values, { includeStatus: false })).not.toHaveProperty('status');
    expect(toCreatePayload(values, { includeStatus: true })).toMatchObject({
      patient_name: 'Jane Perera',
      status: 'confirmed',
    });
  });

  it('builds a patch from changed fields only, comparing times as instants', () => {
    const appointment = makeAppointment(1, { patient_name: 'Jane Perera', start_time: '2099-01-05T15:00:00Z' });
    expect(toPatchPayload(values, appointment)).toEqual({ status: 'confirmed' });
  });
});

describe('fieldErrors', () => {
  it('keeps the first message per field and ignores a missing details list', () => {
    expect(
      fieldErrors({ details: [{ field: 'a', message: 'one' }, { field: 'a', message: 'two' }] }),
    ).toEqual({ a: 'one' });
    expect(fieldErrors(new Error('x'))).toEqual({});
  });
});
