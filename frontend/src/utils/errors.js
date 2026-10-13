/**
 * Turn any thrown value into a message that is safe to show the user.
 * @param {unknown} error
 * @returns {string}
 */
export function errorMessage(error) {
  if (error?.status === 429) return 'Too many attempts, try again shortly.';
  if (error?.code === 'network_error') return 'Could not reach the server. Check your connection.';
  if (error?.status >= 500) return 'Something went wrong on our side. Please try again.';
  return error?.message || 'Something went wrong.';
}
