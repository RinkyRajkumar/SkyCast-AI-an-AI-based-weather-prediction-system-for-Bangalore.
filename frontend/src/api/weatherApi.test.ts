import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient, getClimateNews, getEnvironment, getLocations, getObservations, getPrediction } from './weatherApi'
import type { WeatherLocation, WeatherObservation } from '../types'

afterEach(() => vi.restoreAllMocks())

describe('weather API', () => {
  const london: WeatherLocation = { name: 'London', country: 'United Kingdom', admin1: 'England', latitude: 51.5085, longitude: -0.1257, timezone: 'Europe/London' }

  it('loads backend-proxied Open-Meteo observations', async () => {
    const response = { location: 'Bengaluru, India', latitude: 12.9716, longitude: 77.5946, timezone: 'Asia/Kolkata', model_supported: true, source: 'Open-Meteo', latest_timestamp: '2025-01-01T00:00', observations: [], hourly_forecasts: [], daily_forecasts: [] }
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: response })
    await expect(getObservations(london)).resolves.toEqual(response)
    expect(apiClient.get).toHaveBeenCalledWith('/api/observations', { params: london, signal: undefined })
  })

  it('searches Open-Meteo locations through the backend', async () => {
    const response = { query: 'London', results: [london] }
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: response })
    await expect(getLocations('London')).resolves.toEqual(response)
    expect(apiClient.get).toHaveBeenCalledWith('/api/locations', { params: { query: 'London' }, signal: undefined })
  })

  it('loads backend-proxied environmental insights', async () => {
    const response = { location: 'Bengaluru, India', source: 'Open-Meteo', observed_at: '2026-07-18T00:00', us_aqi: 42, pm2_5: 8, pm10: 19, air_quality_label: 'Good', air_quality_description: 'Air quality is satisfactory for most people.', dust_outlook: 'Low', dust_description: 'Outdoor dust exposure is currently low.', uv_index: 2.4, uv_label: 'Low', uv_description: 'Minimal protection is needed for typical outdoor activity.', pollen_available: false, pollen_outlook: 'Pollen data unavailable', pollen_description: 'No pollen coverage.', pollen_readings: [] }
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: response })
    await expect(getEnvironment(london)).resolves.toEqual(response)
    expect(apiClient.get).toHaveBeenCalledWith('/api/environment', { params: london, signal: undefined })
  })

  it('loads backend-proxied climate and weather news', async () => {
    const response = { source: 'Google News RSS', fetched_at: '2026-07-18T00:00:00Z', articles: [{ title: 'Climate outlook update', url: 'https://example.com/article', source: 'Example News', published_at: '2026-07-18T00:00:00Z' }] }
    vi.spyOn(apiClient, 'get').mockResolvedValue({ data: response })
    await expect(getClimateNews(london)).resolves.toEqual(response)
    expect(apiClient.get).toHaveBeenCalledWith('/api/climate-news', { params: london, signal: undefined })
  })

  it('posts observations and returns forecasts', async () => {
    const observations: WeatherObservation[] = [{ timestamp: '2025-01-01T00:00', temperature: 24, relative_humidity: 70, precipitation: 0, surface_pressure: 920, cloud_cover: 40, wind_speed: 8, wind_direction: 180 }]
    const response = { location: 'Bangalore', generated_at: '2025-01-01T00:00:00Z', forecasts: [] }
    vi.spyOn(apiClient, 'post').mockResolvedValue({ data: response })
    await expect(getPrediction(observations)).resolves.toEqual(response)
    expect(apiClient.post).toHaveBeenCalledWith('/predict', { observations }, { signal: undefined })
  })
})
