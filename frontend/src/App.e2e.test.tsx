import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { App } from './App'

const describeLive = process.env.SKYCAST_E2E === '1' ? describe : describe.skip

describeLive('SkyCast live integration', () => {
  it('loads live observations and displays API forecasts and charts', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Six-day outlook' }, { timeout: 45_000 })).toBeInTheDocument()
    expect(screen.getAllByText('expected rainfall')).toHaveLength(6)
    await waitFor(
      () => {
        expect(screen.getByLabelText('Temperature prediction line chart')).toBeInTheDocument()
        expect(screen.getByLabelText('Rain probability line chart')).toBeInTheDocument()
      },
      { timeout: 10_000 },
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  }, 60_000)
})
