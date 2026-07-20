import { useRef } from 'react'
import type { HourlyForecast, WeatherLocation } from '../types'

interface HourlyForecastStripProps {
  forecasts: HourlyForecast[]
  location: WeatherLocation
}

function weatherClass(weatherCode: number): string {
  if (weatherCode >= 51) return 'hourly-weather-rain'
  if (weatherCode >= 2) return 'hourly-weather-cloud'
  return 'hourly-weather-clear'
}

function timeLabel(timestamp: string, timezone: string): string {
  return new Intl.DateTimeFormat('en-IN', { hour: 'numeric', timeZone: timezone }).format(new Date(timestamp))
}

export function HourlyForecastStrip({ forecasts, location }: HourlyForecastStripProps) {
  const stripRef = useRef<HTMLDivElement>(null)

  function moveHours(direction: number) {
    stripRef.current?.scrollBy({ left: direction * 420, behavior: 'smooth' })
  }

  return (
    <section className="hourly-section" aria-labelledby="hourly-weather-heading">
      <div className="hourly-title-row">
        <div><p className="eyebrow">Hourly weather</p><h2 id="hourly-weather-heading">Next 24 hours</h2></div>
        <span>{location.name} &middot; Live Open-Meteo outlook</span>
      </div>
      <div className="hourly-carousel">
        <button className="hourly-scroll-button hourly-scroll-left" type="button" aria-label="Show earlier hours" onClick={() => moveHours(-1)}>&larr;</button>
        <div ref={stripRef} className="hourly-strip" aria-label={`Hourly ${location.name} weather forecast`}>
          {forecasts.map((forecast) => (
            <article className="hourly-card" key={forecast.timestamp}>
              <strong>{timeLabel(forecast.timestamp, location.timezone)}</strong>
              <span className={`hourly-weather-icon ${weatherClass(forecast.weather_code)}`} aria-hidden="true"><i /></span>
              <b>{Math.round(forecast.temperature)}&deg;</b>
              <small><span aria-hidden="true">&#9679;</span> {Math.round(forecast.precipitation_probability)}%</small>
            </article>
          ))}
        </div>
        <button className="hourly-scroll-button hourly-scroll-right" type="button" aria-label="Show later hours" onClick={() => moveHours(1)}>&rarr;</button>
      </div>
    </section>
  )
}
