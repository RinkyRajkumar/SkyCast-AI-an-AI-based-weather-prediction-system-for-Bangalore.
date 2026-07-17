import type { Forecast, WeatherLocation, WeatherObservation } from '../types'

interface WeatherSceneProps {
  observation: WeatherObservation
  nextForecast?: Forecast
  location: WeatherLocation
}

type SceneCondition = 'clear' | 'cloudy' | 'rainy'

function getSceneCondition(observation: WeatherObservation, nextForecast?: Forecast): SceneCondition {
  if (observation.precipitation > 0 || nextForecast?.rain_probability && nextForecast.rain_probability >= 0.5) {
    return 'rainy'
  }
  return observation.cloud_cover >= 55 ? 'cloudy' : 'clear'
}

function getSceneDescription(condition: SceneCondition, location: WeatherLocation, nextForecast?: Forecast): string {
  if (condition === 'rainy') {
    return nextForecast?.rain_expected ? 'Rain likely in the next hour' : `Light rain around ${location.name}`
  }
  if (condition === 'cloudy') return `Clouds across ${location.name}`
  return `Bright skies over ${location.name}`
}

function formatTime(timestamp: string, timezone: string): string {
  return new Intl.DateTimeFormat('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    weekday: 'long',
    timeZone: timezone,
  }).format(new Date(timestamp))
}

export function WeatherScene({ observation, nextForecast, location }: WeatherSceneProps) {
  const condition = getSceneCondition(observation, nextForecast)
  const description = getSceneDescription(condition, location, nextForecast)

  return (
    <article className={`weather-scene weather-scene-${condition}`} aria-label={description}>
      <div className="weather-scene-copy">
        <p className="eyebrow">Live weather · Open-Meteo</p>
        <h2>{description}</h2>
        <p className="scene-time">{formatTime(observation.timestamp, location.timezone)}</p>
        <div className="scene-temperature">
          {observation.temperature.toFixed(1)}<sup>°C</sup>
        </div>
        <div className="scene-metrics">
          <span>Humidity <strong>{observation.relative_humidity.toFixed(0)}%</strong></span>
          <span>Wind <strong>{observation.wind_speed.toFixed(1)} km/h</strong></span>
        </div>
      </div>

      <div className="scene-art" aria-hidden="true">
        <span className="scene-sun" />
        <span className="scene-cloud scene-cloud-back" />
        <span className="scene-cloud scene-cloud-front" />
        <span className="scene-rain scene-rain-one" />
        <span className="scene-rain scene-rain-two" />
        <span className="scene-rain scene-rain-three" />
        <span className="scene-horizon" />
      </div>
    </article>
  )
}
