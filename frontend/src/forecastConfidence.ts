import type { Forecast, WeatherObservation } from './types'

export type ConfidenceLevel = 'High' | 'Medium' | 'Low'

export interface ForecastConfidence {
  horizonHours: number
  level: ConfidenceLevel
  detail: string
  historyQuality: 'Complete history' | 'Partial history'
  rainSignal: 'Settled rain signal' | 'Mixed rain signal'
}

const REQUIRED_HISTORY_HOURS = 169
const REQUIRED_OBSERVATION_FIELDS: Array<keyof WeatherObservation> = [
  'temperature',
  'relative_humidity',
  'precipitation',
  'surface_pressure',
  'cloud_cover',
  'wind_speed',
  'wind_direction',
]

// Test-set temperature RMSE (°C) for the selected Bangalore models. Lower error
// contributes to confidence, but does not replace live-data quality checks.
const BANGALORE_MODEL_RMSE: Record<number, number> = {
  1: 0.56,
  6: 1.02,
  12: 1.09,
  24: 1.11,
}

const HORIZON_BASE_SCORE: Record<number, number> = {
  1: 0.48,
  6: 0.38,
  12: 0.31,
  24: 0.25,
}

function hasCompleteRecentHistory(observations: WeatherObservation[]): boolean {
  const recent = observations.slice(-REQUIRED_HISTORY_HOURS)
  if (recent.length !== REQUIRED_HISTORY_HOURS) return false

  return recent.every((observation, index) => {
    const valuesAreValid = REQUIRED_OBSERVATION_FIELDS.every((field) => Number.isFinite(observation[field]))
    if (!valuesAreValid || Number.isNaN(Date.parse(observation.timestamp))) return false
    if (index === 0) return true

    const previous = Date.parse(recent[index - 1].timestamp)
    return Date.parse(observation.timestamp) - previous === 60 * 60 * 1000
  })
}

function rainSignalIsSettled(rainProbability: number): boolean {
  return Math.abs(rainProbability - 0.5) >= 0.18
}

function modelScore(horizonHours: number, isModelForecast: boolean): number {
  if (!isModelForecast) return 0.1
  const rmse = BANGALORE_MODEL_RMSE[horizonHours] ?? 1.5
  return Math.max(0, 1 - rmse / 2) * 0.2
}

export function createForecastConfidence(
  forecasts: Forecast[],
  observations: WeatherObservation[],
  isModelForecast: boolean,
): ForecastConfidence[] {
  const historyIsComplete = hasCompleteRecentHistory(observations)

  return forecasts.map((forecast) => {
    const settledRainSignal = rainSignalIsSettled(forecast.rain_probability)
    const score = (HORIZON_BASE_SCORE[forecast.horizon_hours] ?? 0.2)
      + modelScore(forecast.horizon_hours, isModelForecast)
      + (historyIsComplete ? 0.2 : 0.02)
      + (settledRainSignal ? 0.07 : 0)
    const level: ConfidenceLevel = score >= 0.75 ? 'High' : score >= 0.5 ? 'Medium' : 'Low'
    const performance = isModelForecast
      ? `Model error ${BANGALORE_MODEL_RMSE[forecast.horizon_hours]?.toFixed(2) ?? 'n/a'}°C`
      : 'Live provider outlook'

    return {
      horizonHours: forecast.horizon_hours,
      level,
      detail: performance,
      historyQuality: historyIsComplete ? 'Complete history' : 'Partial history',
      rainSignal: settledRainSignal ? 'Settled rain signal' : 'Mixed rain signal',
    }
  })
}
