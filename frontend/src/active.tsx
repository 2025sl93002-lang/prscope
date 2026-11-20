// Active-analysis context: remembers the last opened analysis so the sidebar's
// per-analysis sections (Impact, Verification, …) can link to it.
// SPDX-License-Identifier: MIT
import { createContext, useContext, useState, type ReactNode } from 'react'

interface ActiveCtx {
  activeId: number | null
  setActiveId: (id: number | null) => void
}
const Ctx = createContext<ActiveCtx>({ activeId: null, setActiveId: () => {} })

export function ActiveAnalysisProvider({ children }: { children: ReactNode }) {
  const [activeId, setActiveIdState] = useState<number | null>(() => {
    const v = localStorage.getItem('prscope-active-analysis')
    return v ? Number(v) : null
  })
  const setActiveId = (id: number | null) => {
    setActiveIdState(id)
    if (id == null) localStorage.removeItem('prscope-active-analysis')
    else localStorage.setItem('prscope-active-analysis', String(id))
  }
  return <Ctx.Provider value={{ activeId, setActiveId }}>{children}</Ctx.Provider>
}

export function useActiveAnalysis() {
  return useContext(Ctx)
}
