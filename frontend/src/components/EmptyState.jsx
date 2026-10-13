export default function EmptyState({ title, children }) {
  return (
    <div className="state-card">
      <h2>{title}</h2>
      {children && <p>{children}</p>}
    </div>
  );
}
