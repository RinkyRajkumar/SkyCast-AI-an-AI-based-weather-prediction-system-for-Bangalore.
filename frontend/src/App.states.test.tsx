import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { getHealth, getObservations, getPrediction } from './api/weatherApi'
import type { WeatherObservation } from './types'

vi.mock('./api/weatherApi', async (importOriginal) => {
  const original = await importOriginal<typeof import('./api/weatherApi')>()
  return { ...original, getHealth: vi.fn(), getObservations: vi.fn(), getPrediction: vi.fn() }
})

const mockedHealth = vi.mocked(getHealth)
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

const forecastResponse = {
  location: 'Bangalore',
  generated_at: '2025-01-08T00:00:00Z',
  forecasts: [{ horizon_hours: 1, temperature_c: 24, rain_probability: 0.2, rain_expected: false, rainfall_mm: 0 }],
}

describe('SkyCast automatic weather-loading states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedHealth.mockResolvedValue({ status: 'ok', location: 'Bangalore', models_loaded: true })
  })

  it('loads Open-Meteo observations then automatically requests a forecast', async () => {
    const observations = history()
    mockedObservations.mockResolvedValue({
      location: 'Bengaluru, India', source: 'Open-Meteo', latest_timestamp: observations.at(-1)!.timestamp, observations,
    })
    mockedPrediction.mockResolvedValue(forecastResponse)
    render(<App />)
    expect(screen.getAllByText('Loading Bengaluru weather history…')).not.toHaveLength(0)
    expect(await screen.findByText('169 hourly records loaded')).toBeInTheDocument()
    expect(mockedPrediction).toHaveBeenCalledWith(observations, expect.any(AbortSignal))
    expect(screen.getByText('Weather data provided by Open-Meteo.')).toBeInTheDocument()
  })

  it('shows a retry option when loading observations fails', async () => {
    mockedObservations.mockRejectedValueOnce(new Error('Open-Meteo timed out.'))
    mockedObservations.mockResolvedValue({ location: 'Bengaluru, India', source: 'Open-Meteo', latest_timestamp: history().at(-1)!.timestamp, observations: history() })
    mockedPrediction.mockResolvedValue(forecastResponse)
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Open-Meteo timed out.')
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('169 hourly records loaded')).toBeInTheDocument()
  })
})
