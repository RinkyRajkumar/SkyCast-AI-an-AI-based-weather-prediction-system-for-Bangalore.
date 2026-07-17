import { lazy, Suspense, useEffect, useState } from 'react'
import {
  getApiErrorMessage,
  getEnvironment,
  getObservations,
  getPrediction,
} from './api/weatherApi'
import { ErrorMessage } from './components/ErrorMessage'
import { EnvironmentalInsights } from './components/EnvironmentalInsights'
import { ForecastCard } from './components/ForecastCard'
import { HourlyForecastStrip } from './components/HourlyForecastStrip'
import { LoadingState } from './components/LoadingState'
import { WeatherScene } from './components/WeatherScene'
import type { DailyForecast, EnvironmentalInsights as EnvironmentalInsightsData, HourlyForecast, PredictionResponse, WeatherObservation } from './types'
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
  const [dailyForecasts, setDailyForecasts] = useState<DailyForecast[]>([])
  const [hourlyForecasts, setHourlyForecasts] = useState<HourlyForecast[]>([])
  const [environment, setEnvironment] = useState<EnvironmentalInsightsData | null>(null)
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState<'history' | 'forecast'>('history')
  const [error, setError] = useState('')

  async function predictWithHistory(history: WeatherObservation[], signal?: AbortSignal) {
    setLoadingStage('forecast')
    const response = await getPrediction(history, signal)
    if (!response.forecasts.length) throw new Error('The backend returned an empty forecast.')
    setPrediction(response)
  }

  async function loadWeatherHistory(signal?: AbortSignal) {
    setIsLoading(true)
    setLoadingStage('history')
    setError('')
    try {
      const response = await getObservations(signal)
      setObservations(response.observations)
      setDailyForecasts(response.daily_forecasts)
      setHourlyForecasts(response.hourly_forecasts)
      void getEnvironment(signal)
        .then((environmentResponse) => {
          if (!signal?.aborted) setEnvironment(environmentResponse)
        })
        .catch(() => {
          if (!signal?.aborted) setEnvironment(null)
        })
      await predictWithHistory(response.observations, signal)
    } catch (requestError) {
      if (signal?.aborted) return
      setError(getApiErrorMessage(requestError))
    } finally {
      if (!signal?.aborted) setIsLoading(false)
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    void loadWeatherHistory(controller.signal)
    return () => controller.abort()
  }, [])

  const currentObservation = observations.at(-1)

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="SkyCast AI home">
          <span className="brand-mark"><span /></span>
          <span>SkyCast <strong>AI</strong></span>
        </a>
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

        <section className="weather-overview">
          {currentObservation ? (
            <WeatherScene observation={currentObservation} nextForecast={prediction?.forecasts[0]} />
          ) : (
            <div className="panel weather-placeholder">Live Bengaluru weather will appear here shortly.</div>
          )}
        </section>

        {error ? <ErrorMessage message={error} onDismiss={() => setError('')} onRetry={() => void loadWeatherHistory()} /> : null}
        {isLoading ? (
          <LoadingState
            title={loadingStage === 'history' ? 'Loading Bengaluru weather history…' : 'Generating forecast'}
            description={loadingStage === 'history' ? 'Fetching 169 contiguous hourly records from Open-Meteo.' : 'Running temperature and rain models across four horizons.'}
          />
        ) : null}

        {!isLoading && prediction && dailyForecasts.length ? (
          <section className="forecast-section" aria-live="polite">
            {hourlyForecasts.length ? <HourlyForecastStrip forecasts={hourlyForecasts} /> : null}
            <div className="forecast-title-row">
              <div><p className="eyebrow">Daily weather</p><h2>Six-day outlook</h2></div>
              <span>Bengaluru · Open-Meteo forecast</span>
            </div>
            <div className="forecast-grid">
              {dailyForecasts.map((forecast) => <ForecastCard key={forecast.date} forecast={forecast} />)}
            </div>
            <div className="charts-grid">
              <Suspense fallback={<div className="chart-loading">Loading charts…</div>}>
                <TemperatureChart forecasts={prediction.forecasts} />
                <RainProbabilityChart forecasts={hourlyForecasts} />
              </Suspense>
            </div>
            {environment ? <EnvironmentalInsights insight={environment} dailyForecast={dailyForecasts[0]} /> : null}
          </section>
        ) : null}

        {!isLoading && !dailyForecasts.length && !error ? (
          <section className="empty-state">
            <span className="empty-orbit"><span /></span>
            <div><strong>Your forecast will appear here</strong><p>Live Bengaluru weather history is being loaded for an automatic four-horizon outlook.</p></div>
          </section>
        ) : null}
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <a className="footer-logo" href="#top">SkyCast <strong>AI</strong></a>
            <p>Short-range weather intelligence for Bengaluru, India.</p>
          </div>
          <div className="footer-information">
            <span>Temperature and rainfall forecasts</span>
            <span>Research demonstration · Not for safety-critical decisions</span>
          </div>
          <div className="footer-source">
            <span className="source-status"><i /> Live data source</span>
            <span>Weather data provided by Open-Meteo.</span>
          </div>
          <p className="footer-copyright">&copy; 2026 SkyCast AI</p>
        </div>
      </footer>
    </div>
  )
}
