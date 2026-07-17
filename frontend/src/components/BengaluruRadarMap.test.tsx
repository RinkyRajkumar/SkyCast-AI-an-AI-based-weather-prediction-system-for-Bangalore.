import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BengaluruRadarMap } from './BengaluruRadarMap'

describe('BengaluruRadarMap', () => {
  it('embeds a live Bengaluru radar overlay', () => {
    render(<BengaluruRadarMap />)

    const frame = screen.getByTitle('Live weather radar for Bengaluru')
    expect(frame).toHaveAttribute('src', expect.stringContaining('overlay=radar'))
    expect(frame).toHaveAttribute('src', expect.stringContaining('lat=12.9716'))
    expect(screen.getByRole('link', { name: 'Live radar by Windy' })).toHaveAttribute('href', 'https://www.windy.com')
  })
})
