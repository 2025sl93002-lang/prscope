// Data-fetching & theme hooks. SPDX-License-Identifier: MIT
import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from './api'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: string | null
  reload: () => void
}

/** Runs an async loader on mount and whenever `deps` change. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    loaderRef.current()
      .then((d) => active && setData(d))
      .catch((e) => {
        if (!active) return
        setError(e instanceof ApiError ? e.message : String(e))
      })
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, loading, error, reload }
}

type ThemePref = 'system' | 'light' | 'dark'

export function applyTheme(pref: ThemePref) {
  const mql = window.matchMedia('(prefers-color-scheme: dark)')
  const effective = pref === 'system' ? (mql.matches ? 'dark' : 'light') : pref
  document.documentElement.setAttribute('data-theme', effective)
}

export function useTheme(): [ThemePref, (p: ThemePref) => void] {
  const [pref, setPref] = useState<ThemePref>(
    () => (localStorage.getItem('prscope-theme') as ThemePref) || 'system',
  )
  useEffect(() => {
    applyTheme(pref)
    localStorage.setItem('prscope-theme', pref)
    const mql = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => pref === 'system' && applyTheme('system')
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [pref])
  return [pref, setPref]
}
