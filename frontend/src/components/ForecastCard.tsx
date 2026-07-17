import type { DailyForecast } from '../types'

interface ForecastCardProps {
  forecast: DailyForecast
}

function weatherCopy(forecast: DailyForecast): { title: string; detail: string; graphic: string; className: string } {
  const chance = Math.round(forecast.precipitation_probability)
  const temperatureRange = `High near ${Math.round(forecast.temperature_max)}°, low around ${Math.round(forecast.temperature_min)}°.`
  const rainDetail = chance > 0
    ? `${chance}% chance of rain, with around ${forecast.precipitation_sum.toFixed(1)} mm expected.`
    : 'Dry conditions are expected.'

  if (forecast.weather_code >= 95) return { title: 'Thunderstorms possible', detail: `${temperatureRange} Storm activity is possible; ${rainDetail}`, graphic: 'forecast-thunder', className: 'risk-high' }
  if (forecast.weather_code >= 80) return { title: 'Showers at times', detail: `${temperatureRange} Passing showers are likely; ${rainDetail}`, graphic: 'forecast-rain', className: 'risk-high' }
  if (forecast.weather_code >= 61) return { title: 'Rain expected', detail: `${temperatureRange} Rain is likely during the day; ${rainDetail}`, graphic: 'forecast-rain', className: 'risk-high' }
  if (forecast.weather_code >= 51) return { title: 'Light rain possible', detail: `${temperatureRange} Light showers may develop; ${rainDetail}`, graphic: 'forecast-rain', className: 'risk-moderate' }
  if (forecast.weather_code >= 45) return { title: 'Misty conditions', detail: `${temperatureRange} Reduced visibility is possible; ${rainDetail}`, graphic: 'forecast-cloud', className: 'risk-moderate' }
  if (forecast.weather_code >= 2) return { title: 'Mostly cloudy', detail: `${temperatureRange} Cloud cover will be the main feature; ${rainDetail}`, graphic: 'forecast-cloud', className: 'risk-moderate' }
  if (forecast.weather_code === 1) return { title: 'Partly cloudy', detail: `${temperatureRange} A mix of sun and passing clouds; ${rainDetail}`, graphic: 'forecast-partly', className: 'risk-low' }
  return { title: 'Clear outlook', detail: `${temperatureRange} Bright skies are expected; ${rainDetail}`, graphic: 'forecast-clear', className: 'risk-low' }
}

function dayLabel(date: string): { day: string; date: string } {
  const forecastDate = new Date(`${date}T00:00:00`)
  const today = new Date()
  const isToday = forecastDate.toDateString() === today.toDateString()
  return {
    day: isToday ? 'Today' : new Intl.DateTimeFormat('en-IN', { weekday: 'short' }).format(forecastDate),
    date: new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(forecastDate),
  }
}

export function ForecastCard({ forecast }: ForecastCardProps) {
  const weather = weatherCopy(forecast)
  const day = dayLabel(forecast.date)

  return (
    <article className="forecast-card">
      <div className="forecast-horizon">
        <strong>{day.day}</strong>
        <span>{day.date}</span>
      </div>
      <div className={`forecast-icon ${weather.className} ${weather.graphic}`} aria-hidden="true"><span /></div>
      <div className="forecast-copy">
        <strong>{weather.title}</strong>
        <span>{weather.detail}</span>
      </div>
      <div className="forecast-temperature">
        {forecast.temperature_max.toFixed(0)}<span>&deg;</span><small>{forecast.temperature_min.toFixed(0)}&deg;</small>
      </div>
      <div className="forecast-rain">
        <strong>{Math.round(forecast.precipitation_probability)}%</strong>
        <span>rain chance</span>
      </div>
      <div className="forecast-amount">
        <strong>{forecast.precipitation_sum.toFixed(2)} mm</strong>
        <span>expected rainfall</span>
      </div>
    </article>
  )
}
