import { describe, expect, it } from 'vitest'
import { createForecastConfidence } from './forecastConfidence'
import type { Forecast, WeatherObservation } from './types'

function completeHistory(): WeatherObservation[] {
  return Array.from({ length: 169 }, (_, index) => ({
    timestamp: new Date(Date.UTC(2026, 6, 1, index)).toISOString(),
    temperature: 24,
    relative_humidity: 70,
    precipitation: 0,
    surface_pressure: 920,
    cloud_cover: 40,
    wind_speed: 7,
    wind_direction: 180,
  }))
}

const forecasts: Forecast[] = [
  { horizon_hours: 1, temperature_c: 24, rain_probability: 0.1, rain_expected: false, rainfall_mm: 0 },
  { horizon_hours: 24, temperature_c: 25, rain_probability: 0.5, rain_expected: true, rainfall_mm: 2 },
]

describe('createForecastConfidence', () => {
  it('uses horizon, evaluated model performance, and rainfall certainty for ratings', () => {
    const confidence = createForecastConfidence(forecasts, completeHistory(), true)

    expect(confidence[0]).toMatchObject({ horizonHours: 1, level: 'High', historyQuality: 'Complete history', rainSignal: 'Settled rain signal' })
    expect(confidence[1]).toMatchObject({ horizonHours: 24, level: 'Medium', historyQuality: 'Complete history', rainSignal: 'Mixed rain signal' })
  })

  it('lowers confidence when the required recent history is incomplete', () => {
    const incomplete = completeHistory().slice(1)
    const confidence = createForecastConfidence(forecasts, incomplete, true)

    expect(confidence[0]).toMatchObject({ level: 'Medium', historyQuality: 'Partial history' })
    expect(confidence[1]).toMatchObject({ level: 'Low', historyQuality: 'Partial history' })
  })
})
