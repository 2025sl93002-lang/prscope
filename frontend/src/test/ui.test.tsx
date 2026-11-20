// UI primitive rendering + state tests. SPDX-License-Identifier: MIT
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  AttentionBadge, CategoryBadge, Empty, ErrorBox, Loading, Meter, StatTile, StatusBadge,
} from '../components/ui'

describe('UI primitives', () => {
  it('renders an attention badge with the level label', () => {
    render(<AttentionBadge level="high" />)
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('defaults attention badge to Low when null', () => {
    render(<AttentionBadge level={null} />)
    expect(screen.getByText('Low')).toBeInTheDocument()
  })

  it('maps a status to a readable label', () => {
    render(<StatusBadge status="not_applicable" />)
    expect(screen.getByText('not applicable')).toBeInTheDocument()
  })

  it('renders a category label', () => {
    render(<CategoryBadge category="api_contract" />)
    expect(screen.getByText('API')).toBeInTheDocument()
  })

  it('renders the loading state', () => {
    render(<Loading label="Please wait" />)
    expect(screen.getByText('Please wait')).toBeInTheDocument()
  })

  it('renders an error state as an alert', () => {
    render(<ErrorBox message="boom" />)
    expect(screen.getByRole('alert')).toHaveTextContent('boom')
  })

  it('renders an empty state with title and hint', () => {
    render(<Empty title="Nothing here" hint="add something" />)
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
    expect(screen.getByText('add something')).toBeInTheDocument()
  })

  it('clamps the meter width between 0 and 100', () => {
    const { container } = render(<Meter percent={150} />)
    const bar = container.querySelector('.meter > span') as HTMLElement
    expect(bar.style.width).toBe('100%')
  })

  it('renders a stat tile value and delta', () => {
    render(<StatTile label="Files" value={7} delta="changed" />)
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('changed')).toBeInTheDocument()
  })
})
