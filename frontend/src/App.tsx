import { lazy, Suspense, useEffect, useState } from 'react'
import {
  getApiErrorMessage,
  getClimateNews,
  getEnvironment,
  getObservations,
  getPrediction,
} from './api/weatherApi'
import { EnvironmentalInsights } from './components/EnvironmentalInsights'
import { ErrorMessage } from './components/ErrorMessage'
import { ForecastConfidence } from './components/ForecastConfidence'
import { ForecastCard } from './components/ForecastCard'
import { HourlyForecastStrip } from './components/HourlyForecastStrip'
import { LoadingState } from './components/LoadingState'
import { LocationSearch } from './components/LocationSearch'
import { WeatherScene } from './components/WeatherScene'
import type {
  ClimateNewsItem,
  DailyForecast,
  EnvironmentalInsights as EnvironmentalInsightsData,
  Forecast,
  HourlyForecast,
  PredictionResponse,
  WeatherLocation,
  WeatherObservation,
} from './types'
import './App.css'

const TemperatureChart = lazy(() =>
  import('./components/TemperatureChart').then((module) => ({ default: module.TemperatureChart })),
)
const RainProbabilityChart = lazy(() =>
  import('./components/RainProbabilityChart').then((module) => ({ default: module.RainProbabilityChart })),
)

const DEFAULT_LOCATION: WeatherLocation = {
  name: 'Bengaluru',
  country: 'India',
  latitude: 12.9716,
  longitude: 77.5946,
  timezone: 'Asia/Kolkata',
}

function formatGeneratedAt(value: string, timezone: string): string {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(new Date(value))
}

function liveForecasts(hourlyForecasts: HourlyForecast[]): Forecast[] {
  return [1, 6, 12, 24].map((horizon) => {
    const outlook = hourlyForecasts[Math.min(horizon - 1, hourlyForecasts.length - 1)]
    return {
      horizon_hours: horizon,
      temperature_c: outlook.temperature,
      rain_probability: outlook.precipitation_probability / 100,
      rain_expected: outlook.precipitation_probability >= 50,
      rainfall_mm: 0,
    }
  })
}

export function App() {
  const [selectedLocation, setSelectedLocation] = useState<WeatherLocation>(DEFAULT_LOCATION)
  const [observations, setObservations] = useState<WeatherObservation[]>([])
  const [dailyForecasts, setDailyForecasts] = useState<DailyForecast[]>([])
  const [hourlyForecasts, setHourlyForecasts] = useState<HourlyForecast[]>([])
  const [environment, setEnvironment] = useState<EnvironmentalInsightsData | null>(null)
  const [news, setNews] = useState<ClimateNewsItem[]>([])
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [forecastMode, setForecastMode] = useState<'model' | 'live'>('model')
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStage, setLoadingStage] = useState<'history' | 'forecast'>('history')
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setLoadingStage('history')
    setError('')
    setObservations([])
    setDailyForecasts([])
    setHourlyForecasts([])
    setEnvironment(null)
    setNews([])
    setPrediction(null)

    async function loadWeather() {
      try {
        const response = await getObservations(selectedLocation, controller.signal)
        if (controller.signal.aborted) return
        setObservations(response.observations)
        setDailyForecasts(response.daily_forecasts)
        setHourlyForecasts(response.hourly_forecasts)

        void getEnvironment(selectedLocation, controller.signal)
          .then((environmentResponse) => {
            if (!controller.signal.aborted) setEnvironment(environmentResponse)
          })
          .catch(() => {
            if (!controller.signal.aborted) setEnvironment(null)
          })
        void getClimateNews(selectedLocation, controller.signal)
          .then((newsResponse) => {
            if (!controller.signal.aborted) setNews(newsResponse.articles)
          })
          .catch(() => {
            if (!controller.signal.aborted) setNews([])
          })

        setLoadingStage('forecast')
        if (response.model_supported) {
          const modelForecast = await getPrediction(response.observations, controller.signal)
          if (!modelForecast.forecasts.length) throw new Error('The backend returned an empty forecast.')
          if (!controller.signal.aborted) {
            setForecastMode('model')
            setPrediction(modelForecast)
          }
        } else if (!controller.signal.aborted) {
          setForecastMode('live')
          setPrediction({
            location: response.location,
            generated_at: new Date().toISOString(),
            forecasts: liveForecasts(response.hourly_forecasts),
          })
        }
      } catch (requestError) {
        if (!controller.signal.aborted) setError(getApiErrorMessage(requestError))
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadWeather()
    return () => controller.abort()
  }, [reloadKey, selectedLocation])

  const currentObservation = observations.at(-1)
  const displayLocation = [selectedLocation.name, selectedLocation.country].filter(Boolean).join(', ')
  const forecastStatus = prediction
    ? forecastMode === 'model'
      ? `SkyCast AI forecast generated ${formatGeneratedAt(prediction.generated_at, selectedLocation.timezone)}`
      : `Live Open-Meteo forecast for ${selectedLocation.name}`
    : `Loading live weather for ${selectedLocation.name}`

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="SkyCast AI home">
          <span className="brand-mark"><span /></span>
          <span>SkyCast <strong>AI</strong></span>
        </a>
        <LocationSearch onSelect={setSelectedLocation} />
      </header>

      <main id="top">
        <section className="hero-section">
          <div>
            <p className="eyebrow">{displayLocation} · weather intelligence</p>
            <h1>Weather ahead,<br /><em>made clearer.</em></h1>
          </div>
          <div className="hero-summary">
            <span>{forecastStatus}</span>
          </div>
        </section>

        <section className="weather-overview">
          {currentObservation ? (
            <WeatherScene location={selectedLocation} observation={currentObservation} nextForecast={prediction?.forecasts[0]} />
          ) : (
            <div className="panel weather-placeholder">Live weather for {selectedLocation.name} will appear here shortly.</div>
          )}
        </section>

        {!isLoading && prediction ? (
          <ForecastConfidence
            forecasts={prediction.forecasts}
            observations={observations}
            isModelForecast={forecastMode === 'model'}
          />
        ) : null}

        {error ? <ErrorMessage message={error} onDismiss={() => setError('')} onRetry={() => setReloadKey((value) => value + 1)} /> : null}
        {isLoading ? (
          <LoadingState
            title={loadingStage === 'history' ? `Loading ${selectedLocation.name} weather history…` : 'Generating forecast'}
            description={loadingStage === 'history' ? 'Fetching recent, contiguous hourly observations from Open-Meteo.' : forecastMode === 'model' ? 'Running the Bangalore-trained temperature and rain models.' : 'Preparing the latest location-specific weather outlook.'}
          />
        ) : null}

        {!isLoading && prediction && dailyForecasts.length ? (
          <section className="forecast-section" aria-live="polite">
            {hourlyForecasts.length ? <HourlyForecastStrip forecasts={hourlyForecasts} location={selectedLocation} /> : null}
            <div className="forecast-title-row">
              <div><p className="eyebrow">Daily weather</p><h2>Six-day outlook</h2></div>
              <span>{selectedLocation.name} · Open-Meteo forecast</span>
            </div>
            <div className="forecast-grid">
              {dailyForecasts.map((forecast) => <ForecastCard forecast={forecast} key={forecast.date} timezone={selectedLocation.timezone} />)}
            </div>
            <div className="charts-grid">
              <Suspense fallback={<div className="chart-loading">Loading charts…</div>}>
                <TemperatureChart forecasts={hourlyForecasts} timezone={selectedLocation.timezone} />
                <RainProbabilityChart forecasts={hourlyForecasts} timezone={selectedLocation.timezone} />
              </Suspense>
            </div>
            {environment ? <EnvironmentalInsights dailyForecast={dailyForecasts[0]} insight={environment} location={selectedLocation} news={news} /> : null}
          </section>
        ) : null}

        {!isLoading && !dailyForecasts.length && !error ? (
          <section className="empty-state">
            <span className="empty-orbit"><span /></span>
            <div><strong>Your forecast will appear here</strong><p>Search for a city to load its live weather history and local outlook.</p></div>
          </section>
        ) : null}
      </main>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <a className="footer-logo" href="#top">SkyCast <strong>AI</strong></a>
            <p>Live weather intelligence for {displayLocation}.</p>
          </div>
          <div className="footer-information">
            <span>Location-specific weather outlooks</span>
            <span>{forecastMode === 'model' ? 'SkyCast AI model available for Bengaluru' : 'Live forecast data outside the Bangalore model domain'}</span>
          </div>
          <div className="footer-source">
            <span className="source-status"><i /> Live data source</span>
            <span>Weather data provided by Open-Meteo.</span>
          </div>
          <p className="footer-copyright">© 2026 SkyCast AI</p>
        </div>
      </footer>
    </div>
  )
}
