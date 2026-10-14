const norm = (text) => text.toLowerCase().normalize('NFKD').replace(/\p{M}/gu, '').trim();

/** Distinct specialties, A to Z, for the Specialization dropdown. */
export function specialtiesOf(doctors) {
  return [...new Set(doctors.map((d) => d.specialty))].sort((a, b) => a.localeCompare(b));
}

/**
 * Doctors matching a search. Every part of `name` must appear in the doctor's name (any order,
 * ignoring case, accents and a leading "Dr."), and an empty field matches everyone.
 * @param {import('../api/client').Doctor[]} doctors
 * @param {{ name?: string, specialty?: string, hospitalId?: string }} filters
 */
export function filterDoctors(doctors, { name = '', specialty = '', hospitalId = '' } = {}) {
  const words = norm(name)
    .split(/\s+/)
    .filter((word) => word && word !== 'dr' && word !== 'dr.');
  return doctors.filter((doctor) => {
    const full = norm(doctor.full_name);
    return (
      words.every((word) => full.includes(word)) &&
      (!specialty || doctor.specialty === specialty) &&
      (!hospitalId || doctor.hospitals.some((h) => h.id === hospitalId))
    );
  });
}
