import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient, getHealth, getObservations, getPrediction } from './weatherApi'
import type { WeatherObservation } from '../types'

afterEach(() => vi.restoreAllMocks())

describe('weather API', () => {
  it('requests backend health', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: { status: 'ok', location: 'Bangalore', models_loaded: true } })
    await expect(getHealth()).resolves.toMatchObject({ status: 'ok' })
    expect(apiClient.get).toHaveBeenCalledWith('/health', { signal: undefined })
  })

  it('loads backend-proxied Open-Meteo observations', async () => {
    const response = { location: 'Bengaluru, India', source: 'Open-Meteo', latest_timestamp: '2025-01-01T00:00', observations: [] }
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: response })
    await expect(getObservations()).resolves.toEqual(response)
    expect(apiClient.get).toHaveBeenCalledWith('/api/observations', { signal: undefined })
  })

  it('posts observations and returns forecasts', async () => {
    const observations: WeatherObservation[] = [{ timestamp: '2025-01-01T00:00', temperature: 24, relative_humidity: 70, precipitation: 0, surface_pressure: 920, cloud_cover: 40, wind_speed: 8, wind_direction: 180 }]
    const response = { location: 'Bangalore', generated_at: '2025-01-01T00:00:00Z', forecasts: [] }
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: response })
    await expect(getPrediction(observations)).resolves.toEqual(response)
    expect(apiClient.post).toHaveBeenCalledWith('/predict', { observations }, { signal: undefined })
  })
})
