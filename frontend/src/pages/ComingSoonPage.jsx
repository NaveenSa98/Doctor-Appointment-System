import EmptyState from '../components/EmptyState';

/** Placeholder for routes delivered in later milestones (M6 list, M7 booking). */
export default function ComingSoonPage({ title }) {
  return (
    <div className="container">
      <h1 className="page-title">{title}</h1>
      <EmptyState title="Coming soon">This page is built in a later milestone.</EmptyState>
    </div>
  );
}
