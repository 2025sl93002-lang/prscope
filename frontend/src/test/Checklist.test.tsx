// Checklist interaction test with a mocked API. SPDX-License-Identifier: MIT
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChecklistItem } from '../api'

const state: ChecklistItem[] = [
  { id: 1, text: 'Review payment logic', checked: false, reviewer_note: null, source: 'generated', sort_order: 0, created_at: null },
  { id: 2, text: 'Confirm API compatibility', checked: false, reviewer_note: null, source: 'generated', sort_order: 1, created_at: null },
]

vi.mock('../api', () => ({
  api: {
    listChecklist: vi.fn(async () => state),
    updateChecklistItem: vi.fn(async (id: number, body: { checked?: boolean }) => {
      const item = state.find((i) => i.id === id)!
      if (body.checked != null) item.checked = body.checked
      return item
    }),
    addChecklistItem: vi.fn(async (_aid: number, text: string) => {
      const item: ChecklistItem = { id: 99, text, checked: false, reviewer_note: null, source: 'custom', sort_order: 9, created_at: null }
      state.push(item)
      return item
    }),
    deleteChecklistItem: vi.fn(async (id: number) => {
      const idx = state.findIndex((i) => i.id === id)
      if (idx >= 0) state.splice(idx, 1)
    }),
  },
}))

vi.mock('../components/Toast', () => ({ useToast: () => ({ notify: vi.fn() }) }))

import Checklist from '../pages/analysis/Checklist'
import { api } from '../api'

describe('Checklist tab', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads and renders generated checklist items', async () => {
    render(<Checklist analysisId={1} />)
    expect(await screen.findByText('Review payment logic')).toBeInTheDocument()
    expect(screen.getByText('Confirm API compatibility')).toBeInTheDocument()
  })

  it('toggles an item via the API', async () => {
    render(<Checklist analysisId={1} />)
    await screen.findByText('Review payment logic')
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    await waitFor(() => expect(api.updateChecklistItem).toHaveBeenCalledWith(1, { checked: true }))
  })

  it('adds a custom item', async () => {
    render(<Checklist analysisId={1} />)
    await screen.findByText('Review payment logic')
    fireEvent.change(screen.getByPlaceholderText(/Add a custom checklist item/i), { target: { value: 'My custom check' } })
    fireEvent.click(screen.getByText('Add'))
    await waitFor(() => expect(api.addChecklistItem).toHaveBeenCalledWith(1, 'My custom check'))
  })
})
