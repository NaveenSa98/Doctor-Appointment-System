/** Always rendered: tells visitors the data is synthetic. */
export default function DemoBanner() {
  return (
    <div className="demo-banner" role="note">
      Demo environment: all patients and doctors are synthetic. Do not enter real personal data.
    </div>
  );
}
