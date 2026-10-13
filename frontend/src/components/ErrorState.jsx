import { errorMessage } from '../utils/errors';

export default function ErrorState({ error, onRetry }) {
  return (
    <div className="state-card" role="alert">
      <h2>Something went wrong</h2>
      <p>{errorMessage(error)}</p>
      {onRetry && (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
