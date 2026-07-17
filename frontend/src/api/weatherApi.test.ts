import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient, getEnvironment, getObservations, getPrediction } from './weatherApi'
import type { WeatherObservation } from '../types'

afterEach(() => vi.restoreAllMocks())

describe('weather API', () => {
  it('loads backend-proxied Open-Meteo observations', async () => {
    const response = { location: 'Bengaluru, India', source: 'Open-Meteo', latest_timestamp: '2025-01-01T00:00', observations: [], hourly_forecasts: [], daily_forecasts: [] }
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: response })
    await expect(getObservations()).resolves.toEqual(response)
    expect(apiClient.get).toHaveBeenCalledWith('/api/observations', { signal: undefined })
  })

  it('loads backend-proxied environmental insights', async () => {
    const response = { location: 'Bengaluru, India', source: 'Open-Meteo', observed_at: '2026-07-18T00:00', us_aqi: 42, pm2_5: 8, pm10: 19, air_quality_label: 'Good', air_quality_description: 'Air quality is satisfactory for most people.', dust_outlook: 'Low', dust_description: 'Outdoor dust exposure is currently low.', uv_index: 2.4, uv_label: 'Low', uv_description: 'Minimal protection is needed for typical outdoor activity.' }
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: response })
    await expect(getEnvironment()).resolves.toEqual(response)
    expect(apiClient.get).toHaveBeenCalledWith('/api/environment', { signal: undefined })
  })

  it('posts observations and returns forecasts', async () => {
    const observations: WeatherObservation[] = [{ timestamp: '2025-01-01T00:00', temperature: 24, relative_humidity: 70, precipitation: 0, surface_pressure: 920, cloud_cover: 40, wind_speed: 8, wind_direction: 180 }]
    const response = { location: 'Bangalore', generated_at: '2025-01-01T00:00:00Z', forecasts: [] }
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: response })
    await expect(getPrediction(observations)).resolves.toEqual(response)
    expect(apiClient.post).toHaveBeenCalledWith('/predict', { observations }, { signal: undefined })
  })
})
