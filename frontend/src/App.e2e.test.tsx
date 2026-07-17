import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

const describeLive = process.env.SKYCAST_E2E === '1' ? describe : describe.skip

describeLive('SkyCast live integration', () => {
  it('loads live observations and displays API forecasts and charts', async () => {
    render(<App />)
    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
    expect(await screen.findByText('169 hourly records loaded', {}, { timeout: 30_000 })).toBeInTheDocument()
    expect(await screen.findByText('+1 hours', {}, { timeout: 45_000 })).toBeInTheDocument()
    expect(screen.getByText('+24 hours')).toBeInTheDocument()
    await waitFor(
      () => {
        expect(screen.getByLabelText('Temperature prediction line chart')).toBeInTheDocument()
        expect(screen.getByLabelText('Rain probability bar chart')).toBeInTheDocument()
      },
      { timeout: 10_000 },
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  }, 60_000)
})
