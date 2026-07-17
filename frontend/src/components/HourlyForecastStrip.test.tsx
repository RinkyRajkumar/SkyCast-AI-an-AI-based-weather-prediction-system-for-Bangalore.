import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { HourlyForecastStrip } from './HourlyForecastStrip'

describe('HourlyForecastStrip', () => {
  it('renders compact near-term weather cards', () => {
    render(
      <HourlyForecastStrip
        forecasts={[
          { timestamp: '2026-07-18T04:00:00', temperature: 21.4, precipitation_probability: 20, weather_code: 2 },
          { timestamp: '2026-07-18T05:00:00', temperature: 22.1, precipitation_probability: 35, weather_code: 61 },
        ]}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Next 24 hours' })).toBeInTheDocument()
    expect(screen.getByText('21°')).toBeInTheDocument()
    expect(screen.getByText('35%')).toBeInTheDocument()
  })

  it('moves the hourly strip from the left and right controls', async () => {
    const scrollBy = vi.fn()
    Object.defineProperty(HTMLElement.prototype, 'scrollBy', { configurable: true, value: scrollBy })
    const user = userEvent.setup()
    render(<HourlyForecastStrip forecasts={[{ timestamp: '2026-07-18T04:00:00', temperature: 21, precipitation_probability: 20, weather_code: 2 }]} />)

    await user.click(screen.getByRole('button', { name: 'Show later hours' }))
    await user.click(screen.getByRole('button', { name: 'Show earlier hours' }))

    expect(scrollBy).toHaveBeenNthCalledWith(1, { left: 420, behavior: 'smooth' })
    expect(scrollBy).toHaveBeenNthCalledWith(2, { left: -420, behavior: 'smooth' })
  })
})
