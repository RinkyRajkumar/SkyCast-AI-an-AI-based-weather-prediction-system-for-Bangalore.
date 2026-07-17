import type { WeatherObservation } from '../types'

interface CurrentWeatherCardProps {
  observation: WeatherObservation
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  return Number.isNaN(date.getTime())
    ? 'Timestamp pending'
    : new Intl.DateTimeFormat('en-IN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(date)
}

export function CurrentWeatherCard({ observation }: CurrentWeatherCardProps) {
  return (
    <article className="panel current-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Latest observation</p>
          <h2>Current conditions</h2>
        </div>
        <span className="location-pill">Bengaluru</span>
      </div>

      <div className="current-temperature">
        <span>{observation.temperature.toFixed(1)}</span>
        <sup>°C</sup>
      </div>
      <p className="observation-time">{formatTime(observation.timestamp)}</p>

      <dl className="weather-stat-grid">
        <div>
          <dt>Humidity</dt>
          <dd>{observation.relative_humidity.toFixed(0)}%</dd>
        </div>
        <div>
          <dt>Pressure</dt>
          <dd>{observation.surface_pressure.toFixed(1)} hPa</dd>
        </div>
        <div>
          <dt>Cloud cover</dt>
          <dd>{observation.cloud_cover.toFixed(0)}%</dd>
        </div>
        <div>
          <dt>Wind</dt>
          <dd>{observation.wind_speed.toFixed(1)} km/h</dd>
        </div>
      </dl>
    </article>
  )
}
