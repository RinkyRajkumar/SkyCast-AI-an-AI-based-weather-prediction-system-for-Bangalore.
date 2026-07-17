import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SunMoonPanel } from './SunMoonPanel'

describe('SunMoonPanel', () => {
  it('shows live sun times and the calculated moon phase', () => {
    render(<SunMoonPanel location={{ name: 'Bengaluru', country: 'India', latitude: 12.9716, longitude: 77.5946, timezone: 'Asia/Kolkata' }} forecast={{ date: '2026-07-18', weather_code: 1, temperature_max: 28, temperature_min: 20, precipitation_probability: 10, precipitation_sum: 0, sunrise: '2026-07-18T05:59:00+05:30', sunset: '2026-07-18T18:50:00+05:30', daylight_duration_seconds: 46_260 }} />)

    expect(screen.getByRole('region', { name: 'Sun & Moon' })).toBeInTheDocument()
    expect(screen.getByText('12h 51m of daylight')).toBeInTheDocument()
    expect(screen.getByText('Rise')).toBeInTheDocument()
    expect(screen.getByText('Approximate lunar phase')).toBeInTheDocument()
  })
})
