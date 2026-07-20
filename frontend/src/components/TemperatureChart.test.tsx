import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TemperatureChart } from './TemperatureChart'

describe('TemperatureChart', () => {
  it('labels the chart in whole Celsius degrees', () => {
    render(<TemperatureChart timezone="Asia/Kolkata" forecasts={[{ timestamp: '2026-07-18T01:00:00+05:30', temperature: 20.8, precipitation_probability: 0, weather_code: 1 }]} />)

    expect(screen.getByText('°C')).toBeInTheDocument()
    expect(screen.getByLabelText('Temperature prediction line chart')).toBeInTheDocument()
    expect(screen.getByText('Temperature outlook · next 24 hours')).toBeInTheDocument()
  })
})
