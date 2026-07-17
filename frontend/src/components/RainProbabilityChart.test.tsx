import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RainProbabilityChart } from './RainProbabilityChart'

describe('RainProbabilityChart', () => {
  it('renders a line-chart container for probability forecasts', () => {
    render(<RainProbabilityChart forecasts={[{ timestamp: '2026-07-18T01:00:00', temperature: 20, precipitation_probability: 42, weather_code: 61 }]} />)

    expect(screen.getByLabelText('Rain probability line chart')).toBeInTheDocument()
    expect(screen.getByText('Rain probability')).toBeInTheDocument()
    expect(screen.getByText('Precipitation outlook · next 24 hours')).toBeInTheDocument()
  })
})
