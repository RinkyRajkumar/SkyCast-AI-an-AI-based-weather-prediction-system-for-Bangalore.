import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { WeatherInputForm } from './WeatherInputForm'
import type { WeatherObservation } from '../types'

const observation: WeatherObservation = {
  timestamp: '2025-01-01T00:00',
  temperature: 24,
  relative_humidity: 70,
  precipitation: 0,
  surface_pressure: 920,
  cloud_cover: 40,
  wind_speed: 8,
  wind_direction: 180,
}

describe('WeatherInputForm', () => {
  it('keeps prediction disabled until sufficient history is loaded', () => {
    render(
      <WeatherInputForm
        observation={observation}
        observationCount={1}
        isLoading={false}
        onHistoryLoaded={vi.fn()}
      />,
    )

    expect(screen.getByText('Loading Bengaluru weather history…')).toBeInTheDocument()
    expect(screen.getByText('Developer tools')).not.toHaveAttribute('open')
  })

  it('reports an invalid observation file', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <WeatherInputForm
        observation={observation}
        observationCount={1}
        isLoading={false}
        onHistoryLoaded={vi.fn()}
      />,
    )
    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, new File(['{"invalid": true}'], 'weather.json', { type: 'application/json' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Use an array of valid hourly observations')
  })
})
