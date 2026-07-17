import type { Forecast } from '../types'

interface ForecastCardProps {
  forecast: Forecast
}

function rainRisk(probability: number): { label: string; className: string } {
  if (probability >= 0.7) return { label: 'High risk', className: 'risk-high' }
  if (probability >= 0.4) return { label: 'Moderate', className: 'risk-moderate' }
  return { label: 'Low risk', className: 'risk-low' }
}

export function ForecastCard({ forecast }: ForecastCardProps) {
  const risk = rainRisk(forecast.rain_probability)
  return (
    <article className="forecast-card">
      <div className="forecast-card-header">
        <span className="horizon-label">+{forecast.horizon_hours} hours</span>
        <span className={`risk-badge ${risk.className}`}>{risk.label}</span>
      </div>
      <div className="forecast-temperature">
        {forecast.temperature_c.toFixed(1)}<span>°C</span>
      </div>
      <div className="forecast-details">
        <div>
          <span>Rain chance</span>
          <strong>{Math.round(forecast.rain_probability * 100)}%</strong>
        </div>
        <div>
          <span>Expected</span>
          <strong>{forecast.rainfall_mm.toFixed(2)} mm</strong>
        </div>
      </div>
      <div className={`rain-status ${forecast.rain_expected ? 'rain-status-wet' : ''}`}>
        <span className="status-dot" />
        {forecast.rain_expected ? 'Rain expected' : 'No rain expected'}
      </div>
    </article>
  )
}
