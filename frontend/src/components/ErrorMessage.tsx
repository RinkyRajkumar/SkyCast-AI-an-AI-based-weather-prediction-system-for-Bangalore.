interface ErrorMessageProps {
  message: string
  onDismiss?: () => void
  onRetry?: () => void
}

export function ErrorMessage({ message, onDismiss, onRetry }: ErrorMessageProps) {
  return (
    <div className="error-message" role="alert">
      <div>
        <strong>Forecast unavailable</strong>
        <p>{message}</p>
      </div>
      {onRetry ? <button className="retry-button" type="button" onClick={onRetry}>Retry</button> : null}
      {onDismiss ? (
        <button type="button" onClick={onDismiss} aria-label="Dismiss error">×</button>
      ) : null}
    </div>
  )
}
