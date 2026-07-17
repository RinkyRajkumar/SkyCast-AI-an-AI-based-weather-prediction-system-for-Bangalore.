interface LoadingStateProps {
  title?: string
  description?: string
}

export function LoadingState({
  title = 'Generating forecast',
  description = 'Running temperature and rain models across four horizons.',
}: LoadingStateProps) {
  return (
    <section className="loading-panel" aria-live="polite" aria-busy="true">
      <span className="loading-spinner" />
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
    </section>
  )
}
