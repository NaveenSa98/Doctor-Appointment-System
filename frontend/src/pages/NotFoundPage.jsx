import { Link } from 'react-router-dom';
import EmptyState from '../components/EmptyState';

export default function NotFoundPage() {
  return (
    <div className="container">
      <EmptyState title="Page not found">
        That page does not exist. <Link to="/">Go home</Link>.
      </EmptyState>
    </div>
  );
}
