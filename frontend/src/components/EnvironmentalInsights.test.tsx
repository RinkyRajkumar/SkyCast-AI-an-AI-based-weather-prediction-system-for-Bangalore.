import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EnvironmentalInsights } from './EnvironmentalInsights'

describe('EnvironmentalInsights', () => {
  it('renders Open-Meteo air quality and dust guidance', () => {
    render(
      <EnvironmentalInsights
        insight={{
          location: 'Bengaluru, India',
          source: 'Open-Meteo Air Quality',
          observed_at: '2026-07-18T09:00:00',
          us_aqi: 42,
          pm2_5: 8,
          pm10: 19,
          air_quality_label: 'Good',
          air_quality_description: 'Air quality is satisfactory for most people.',
          dust_outlook: 'Low',
          dust_description: 'Outdoor dust exposure is currently low.',
          uv_index: 2.4,
          uv_label: 'Low',
          uv_description: 'Minimal protection is needed for typical outdoor activity.',
        }}
      />,
    )

    expect(screen.getByText('US AQI 42')).toBeInTheDocument()
    expect(screen.getByText('Outdoor dust')).toBeInTheDocument()
    expect(screen.getAllByText('Low')).toHaveLength(2)
    expect(screen.getByText('Current UV index')).toBeInTheDocument()
    expect(screen.getByLabelText('UV index 2.4, Low')).toBeInTheDocument()
  })
})
