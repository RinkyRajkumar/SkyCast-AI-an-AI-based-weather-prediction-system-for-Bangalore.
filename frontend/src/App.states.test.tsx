import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { getClimateNews, getEnvironment, getObservations, getPrediction } from './api/weatherApi'
import type { WeatherObservation } from './types'

vi.mock('./api/weatherApi', async (importOriginal) => {
  const original = await importOriginal<typeof import('./api/weatherApi')>()
  return { ...original, getClimateNews: vi.fn(), getEnvironment: vi.fn(), getObservations: vi.fn(), getPrediction: vi.fn() }
})

const mockedEnvironment = vi.mocked(getEnvironment)
const mockedClimateNews = vi.mocked(getClimateNews)
const mockedObservations = vi.mocked(getObservations)
const mockedPrediction = vi.mocked(getPrediction)

function history(): WeatherObservation[] {
  return Array.from({ length: 169 }, (_, index) => ({
    timestamp: `2025-01-${String(1 + Math.floor(index / 24)).padStart(2, '0')}T${String(index % 24).padStart(2, '0')}:00`,
    temperature: 22 + index / 100,
    relative_humidity: 70,
    precipitation: 0,
    surface_pressure: 920,
    cloud_cover: 40,
    wind_speed: 8,
    wind_direction: 180,
  }))
}

function dailyForecasts() {
  return Array.from({ length: 6 }, (_, index) => ({
    date: `2025-01-${String(index + 1).padStart(2, '0')}`,
    weather_code: index === 0 ? 0 : 61,
    temperature_max: 26 + index,
    temperature_min: 18 + index,
    precipitation_probability: 20 + index * 10,
    precipitation_sum: index / 2,
    sunrise: `2025-01-${String(index + 1).padStart(2, '0')}T06:00:00`,
    sunset: `2025-01-${String(index + 1).padStart(2, '0')}T18:00:00`,
    daylight_duration_seconds: 43_200,
  }))
}

function hourlyForecasts() {
  return Array.from({ length: 24 }, (_, index) => ({
    timestamp: `2025-01-08T${String(index).padStart(2, '0')}:00`,
    temperature: 20 + index / 2,
    precipitation_probability: 5 + index,
    weather_code: index > 7 ? 61 : 1,
  }))
}

const forecastResponse = {
  location: 'Bangalore',
  generated_at: '2025-01-08T00:00:00Z',
  forecasts: [{ horizon_hours: 1, temperature_c: 24, rain_probability: 0.2, rain_expected: false, rainfall_mm: 0 }],
}

const environmentResponse = {
  location: 'Bengaluru, India', source: 'Open-Meteo Air Quality', observed_at: '2026-07-18T00:00:00',
  us_aqi: 42, pm2_5: 8, pm10: 19, air_quality_label: 'Good',
  air_quality_description: 'Air quality is satisfactory for most people.',
  dust_outlook: 'Low', dust_description: 'Outdoor dust exposure is currently low.',
  uv_index: 2.4, uv_label: 'Low', uv_description: 'Minimal protection is needed for typical outdoor activity.',
  pollen_available: false, pollen_outlook: 'Pollen data unavailable',
  pollen_description: 'The live weather provider does not currently supply pollen coverage for Bengaluru.', pollen_readings: [],
}

const climateNewsResponse = {
  source: 'Google News RSS', fetched_at: '2026-07-18T00:00:00Z',
  articles: [{ title: 'Climate outlook update', url: 'https://example.com/article', source: 'Example News', published_at: '2026-07-18T00:00:00Z' }],
}

describe('SkyCast automatic weather-loading states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedEnvironment.mockResolvedValue(environmentResponse)
    mockedClimateNews.mockResolvedValue(climateNewsResponse)
  })

  it('loads Open-Meteo observations then automatically requests a forecast', async () => {
    const observations = history()
    mockedObservations.mockResolvedValue({
      location: 'Bengaluru, India', latitude: 12.9716, longitude: 77.5946, timezone: 'Asia/Kolkata', model_supported: true, source: 'Open-Meteo', latest_timestamp: observations.at(-1)!.timestamp, observations, hourly_forecasts: hourlyForecasts(), daily_forecasts: dailyForecasts(),
    })
    mockedPrediction.mockResolvedValue(forecastResponse)
    render(<App />)
    expect(screen.getAllByText('Loading Bengaluru weather history…')).not.toHaveLength(0)
    expect(await screen.findByText('Bright skies over Bengaluru')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Next 24 hours' })).toBeInTheDocument()
    expect(mockedPrediction).toHaveBeenCalledWith(observations, expect.any(AbortSignal))
    expect(await screen.findByText('US AQI 42')).toBeInTheDocument()
    expect(await screen.findByText('Climate outlook update')).toBeInTheDocument()
    expect(screen.getByText('Weather data provided by Open-Meteo.')).toBeInTheDocument()
  })

  it('shows a retry option when loading observations fails', async () => {
    mockedObservations.mockRejectedValueOnce(new Error('Open-Meteo timed out.'))
    mockedObservations.mockResolvedValue({ location: 'Bengaluru, India', latitude: 12.9716, longitude: 77.5946, timezone: 'Asia/Kolkata', model_supported: true, source: 'Open-Meteo', latest_timestamp: history().at(-1)!.timestamp, observations: history(), hourly_forecasts: hourlyForecasts(), daily_forecasts: dailyForecasts() })
    mockedPrediction.mockResolvedValue(forecastResponse)
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Open-Meteo timed out.')
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Bright skies over Bengaluru')).toBeInTheDocument()
  })

})
