import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { getLocations } from '../api/weatherApi'
import { LocationSearch } from './LocationSearch'

vi.mock('../api/weatherApi', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api/weatherApi')>()
  return { ...original, getLocations: vi.fn() }
})

describe('LocationSearch', () => {
  it('searches for and selects a location result', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    vi.mocked(getLocations).mockResolvedValue({
      query: 'London',
      results: [{ name: 'London', admin1: 'England', country: 'United Kingdom', latitude: 51.5085, longitude: -0.1257, timezone: 'Europe/London' }],
    })
    render(<LocationSearch onSelect={onSelect} />)

    await user.type(screen.getByRole('searchbox'), 'London')
    expect(await screen.findByRole('option', { name: /London, England, United Kingdom/i })).toBeInTheDocument()
    await user.click(screen.getByRole('option', { name: /London, England, United Kingdom/i }))

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ name: 'London', timezone: 'Europe/London' }))
  })
})
