import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TemperatureChart } from './TemperatureChart'

describe('TemperatureChart', () => {
  it('labels the chart in whole Celsius degrees', () => {
    render(<TemperatureChart forecasts={[{ horizon_hours: 1, temperature_c: 20.8, rain_probability: 0, rain_expected: false, rainfall_mm: 0 }]} />)

    expect(screen.getByText('°C')).toBeInTheDocument()
    expect(screen.getByLabelText('Temperature prediction line chart')).toBeInTheDocument()
  })
})
