import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ForecastCard } from './ForecastCard'

describe('ForecastCard', () => {
  it('renders forecast values in the forecast-list row', () => {
    render(
      <ForecastCard
        timezone="Asia/Kolkata"
        forecast={{
          date: '2026-07-18',
          weather_code: 61,
          temperature_max: 24.6,
          temperature_min: 19.2,
          precipitation_probability: 71,
          precipitation_sum: 1.8,
          sunrise: '2026-07-18T06:00:00',
          sunset: '2026-07-18T18:00:00',
          daylight_duration_seconds: 43_200,
        }}
      />,
    )

    expect(screen.getByText('Today')).toBeInTheDocument()
    expect(screen.getByText('25')).toBeInTheDocument()
    expect(screen.getByText('71%')).toBeInTheDocument()
    expect(screen.getByText('1.80 mm')).toBeInTheDocument()
    expect(screen.getByText('Rain expected')).toBeInTheDocument()
    expect(screen.getByText('High near 25°, low around 19°. Rain is likely during the day; 71% chance of rain, with around 1.8 mm expected.')).toBeInTheDocument()
    expect(screen.getByText('expected rainfall')).toBeInTheDocument()
  })
})
