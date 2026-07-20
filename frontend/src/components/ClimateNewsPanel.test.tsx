import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ClimateNewsPanel } from './ClimateNewsPanel'

describe('ClimateNewsPanel', () => {
  it('renders current linked climate and weather headlines', () => {
    render(
      <ClimateNewsPanel
        location={{ name: 'Bengaluru', country: 'India', latitude: 12.9716, longitude: 77.5946, timezone: 'Asia/Kolkata' }}
        articles={[{
          title: 'Climate outlook update',
          url: 'https://example.com/climate-outlook',
          source: 'Example News',
          published_at: '2026-07-18T00:00:00Z',
        }]}
      />,
    )

    expect(screen.getByRole('region', { name: 'Climate & weather news' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Climate outlook update/i })).toHaveAttribute('href', 'https://example.com/climate-outlook')
    expect(screen.getByText(/Example News/)).toBeInTheDocument()
  })
})
