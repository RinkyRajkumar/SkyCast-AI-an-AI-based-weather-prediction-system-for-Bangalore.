import type { Forecast, WeatherObservation } from '../types'

interface WeatherSceneProps {
  observation: WeatherObservation
  nextForecast?: Forecast
}

type SceneCondition = 'clear' | 'cloudy' | 'rainy'

function getSceneCondition(observation: WeatherObservation, nextForecast?: Forecast): SceneCondition {
  if (observation.precipitation > 0 || nextForecast?.rain_probability && nextForecast.rain_probability >= 0.5) {
    return 'rainy'
  }
  return observation.cloud_cover >= 55 ? 'cloudy' : 'clear'
}

function getSceneDescription(condition: SceneCondition, nextForecast?: Forecast): string {
  if (condition === 'rainy') {
    return nextForecast?.rain_expected ? 'Rain likely in the next hour' : 'Light rain around Bengaluru'
  }
  if (condition === 'cloudy') return 'Clouds across Bengaluru'
  return 'Bright skies over Bengaluru'
}

function formatTime(timestamp: string): string {
  return new Intl.DateTimeFormat('en-IN', {
    hour: 'numeric',
    minute: '2-digit',
    weekday: 'long',
  }).format(new Date(timestamp))
}

export function WeatherScene({ observation, nextForecast }: WeatherSceneProps) {
  const condition = getSceneCondition(observation, nextForecast)
  const description = getSceneDescription(condition, nextForecast)

  return (
    <article className={`weather-scene weather-scene-${condition}`} aria-label={description}>
      <div className="weather-scene-copy">
        <p className="eyebrow">Live weather · Open-Meteo</p>
        <h2>{description}</h2>
        <p className="scene-time">{formatTime(observation.timestamp)}</p>
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
