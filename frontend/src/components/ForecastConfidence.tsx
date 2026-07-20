import { createForecastConfidence } from '../forecastConfidence'
import type { Forecast, WeatherObservation } from '../types'

interface ForecastConfidenceProps {
  forecasts: Forecast[]
  observations: WeatherObservation[]
  isModelForecast: boolean
}

function confidenceClass(level: string): string {
  return level.toLowerCase().replace(' ', '-')
}

export function ForecastConfidence({ forecasts, observations, isModelForecast }: ForecastConfidenceProps) {
  const confidence = createForecastConfidence(forecasts, observations, isModelForecast)

  if (!confidence.length) return null

  return (
    <section className="forecast-confidence panel" aria-labelledby="forecast-confidence-heading">
      <div className="confidence-heading">
        <div>
          <p className="eyebrow">Forecast confidence</p>
          <h2 id="forecast-confidence-heading">How certain is the outlook?</h2>
        </div>
        <span>{isModelForecast ? 'Bengaluru model evaluation' : 'Live forecast assessment'}</span>
      </div>
      <div className="confidence-grid">
        {confidence.map((item) => (
          <article className="confidence-card" key={item.horizonHours}>
            <span className="confidence-horizon">+{item.horizonHours}h</span>
            <div className="confidence-level-row">
              <strong className={`confidence-level confidence-${confidenceClass(item.level)}`}>{item.level}</strong>
              <span className={`confidence-band confidence-${confidenceClass(item.level)}`} aria-label={`${item.level} confidence`}><i /><i /><i /></span>
            </div>
            <p>{item.detail}</p>
            <small>{item.historyQuality} · {item.rainSignal}</small>
          </article>
        ))}
      </div>
    </section>
  )
}
