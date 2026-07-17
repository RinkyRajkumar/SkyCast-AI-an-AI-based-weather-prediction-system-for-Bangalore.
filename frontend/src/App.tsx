import { lazy, Suspense, useEffect, useState } from 'react'
import {
  getApiErrorMessage,
  getHealth,
  getObservations,
  getPrediction,
  isBackendUnavailable,
} from './api/weatherApi'
import { CurrentWeatherCard } from './components/CurrentWeatherCard'
import { ErrorMessage } from './components/ErrorMessage'
import { ForecastCard } from './components/ForecastCard'
import { LoadingState } from './components/LoadingState'
import { WeatherInputForm } from './components/WeatherInputForm'
import type { ConnectionStatus, PredictionResponse, WeatherObservation } from './types'
import './App.css'

const TemperatureChart = lazy(() =>
  import('./components/TemperatureChart').then((module) => ({ default: module.TemperatureChart })),
)
const RainProbabilityChart = lazy(() =>
  import('./components/RainProbabilityChart').then((module) => ({ default: module.RainProbabilityChart })),
)

function formatGeneratedAt(value: string): string {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

export function App() {
  const [observations, setObservations] = useState<WeatherObservation[]>([])
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [connection, setConnection] = useState<ConnectionStatus>('checking')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState<'history' | 'forecast'>('history')
  const [source, setSource] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal)
      .then(() => setConnection('online'))
      .catch(() => {
        if (!controller.signal.aborted) setConnection('offline')
      })
    return () => controller.abort()
  }, [])

  async function predictWithHistory(history: WeatherObservation[], signal?: AbortSignal) {
    setLoadingStage('forecast')
    const response = await getPrediction(history, signal)
    if (!response.forecasts.length) throw new Error('The backend returned an empty forecast.')
    setPrediction(response)
    setConnection('online')
  }

  async function loadWeatherHistory(signal?: AbortSignal) {
    setIsLoading(true)
    setLoadingStage('history')
    setError('')
    try {
      const response = await getObservations(signal)
      setObservations(response.observations)
      setSource(response.source)
      await predictWithHistory(response.observations, signal)
    } catch (requestError) {
      if (signal?.aborted) return
      setError(getApiErrorMessage(requestError))
      setConnection(isBackendUnavailable(requestError) ? 'offline' : 'online')
    } finally {
      if (!signal?.aborted) setIsLoading(false)
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    void loadWeatherHistory(controller.signal)
    return () => controller.abort()
  }, [])

  function loadDeveloperHistory(history: WeatherObservation[]) {
    const sorted = [...history].sort((left, right) => Date.parse(left.timestamp) - Date.parse(right.timestamp))
    setObservations(sorted)
    setPrediction(null)
    setSource('Developer JSON')
    setError('')
    setIsLoading(true)
    void predictWithHistory(sorted)
      .catch((requestError: unknown) => {
        setError(getApiErrorMessage(requestError))
        setConnection(isBackendUnavailable(requestError) ? 'offline' : 'online')
      })
      .finally(() => setIsLoading(false))
  }

  const currentObservation = observations.at(-1)

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="SkyCast AI home">
          <span className="brand-mark"><span /></span>
          <span>SkyCast <strong>AI</strong></span>
        </a>
        <div className={`connection-status connection-${connection}`}>
          <span />
          {connection === 'checking' ? 'Checking backend' : connection === 'online' ? 'Backend connected' : 'Backend unavailable'}
        </div>
      </header>

      <main id="top">
        <section className="hero-section">
          <div>
            <p className="eyebrow">Bengaluru · AI weather intelligence</p>
            <h1>Weather ahead,<br /><em>made clearer.</em></h1>
          </div>
          <div className="hero-summary">
            <p>Short-range temperature and rainfall forecasts built from eleven years of Bengaluru weather patterns.</p>
            <span>{prediction ? `Generated ${formatGeneratedAt(prediction.generated_at)}` : 'Loading live Bengaluru weather history'}</span>
          </div>
        </section>

        <section className="input-layout">
          <WeatherInputForm
            observation={currentObservation}
            observationCount={observations.length}
            isLoading={isLoading}
            source={source}
            onHistoryLoaded={loadDeveloperHistory}
          />
          {currentObservation ? (
            <CurrentWeatherCard observation={currentObservation} />
          ) : (
            <div className="panel weather-placeholder">Current conditions will appear after weather history loads.</div>
          )}
        </section>

        {error ? <ErrorMessage message={error} onDismiss={() => setError('')} onRetry={() => void loadWeatherHistory()} /> : null}
        {isLoading ? (
          <LoadingState
            title={loadingStage === 'history' ? 'Loading Bengaluru weather history…' : 'Generating forecast'}
            description={loadingStage === 'history' ? 'Fetching 169 contiguous hourly records from Open-Meteo.' : 'Running temperature and rain models across four horizons.'}
          />
        ) : null}

        {!isLoading && prediction ? (
          <section className="forecast-section" aria-live="polite">
            <div className="forecast-title-row">
              <div><p className="eyebrow">Model ensemble</p><h2>Forecast horizons</h2></div>
              <span>{prediction.location} · {prediction.forecasts.length} predictions</span>
            </div>
            <div className="forecast-grid">
              {prediction.forecasts.map((forecast) => <ForecastCard key={forecast.horizon_hours} forecast={forecast} />)}
            </div>
            <div className="charts-grid">
              <Suspense fallback={<div className="chart-loading">Loading charts…</div>}>
                <TemperatureChart forecasts={prediction.forecasts} />
                <RainProbabilityChart forecasts={prediction.forecasts} />
              </Suspense>
            </div>
          </section>
        ) : null}

        {!isLoading && !prediction && !error ? (
          <section className="empty-state">
            <span className="empty-orbit"><span /></span>
            <div><strong>Your forecast will appear here</strong><p>Live Bengaluru weather history is being loaded for an automatic four-horizon outlook.</p></div>
          </section>
        ) : null}
      </main>

      <footer>
        <span>SkyCast AI · Bangalore</span>
        <span>Temperature and rain forecasting research</span>
        <span>Weather data provided by Open-Meteo.</span>
      </footer>
    </div>
  )
}
