import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ForecastCard } from './ForecastCard'

describe('ForecastCard', () => {
  it('renders forecast values and a colour-coded rain status', () => {
    render(
      <ForecastCard
        forecast={{
          horizon_hours: 6,
          temperature_c: 24.6,
          rain_probability: 0.71,
          rain_expected: true,
          rainfall_mm: 1.8,
        }}
      />,
    )

    expect(screen.getByText('+6 hours')).toBeInTheDocument()
    expect(screen.getByText('24.6')).toBeInTheDocument()
    expect(screen.getByText('71%')).toBeInTheDocument()
    expect(screen.getByText('1.80 mm')).toBeInTheDocument()
    expect(screen.getByText('Rain expected')).toBeInTheDocument()
    expect(screen.getByText('High risk')).toHaveClass('risk-high')
  })
})
