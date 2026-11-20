// Settings page — theme + optional local AI. SPDX-License-Identifier: MIT
import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAsync, useTheme } from '../hooks'
import { useToast } from '../components/Toast'
import { Card, CardHead, ErrorBox, Loading } from '../components/ui'

export default function Settings() {
  const { notify } = useToast()
  const [themePref, setThemePref] = useTheme()
  const settings = useAsync(() => api.getSettings(), [])
  const aiStatus = useAsync(() => api.aiStatus(), [])

  const [aiEnabled, setAiEnabled] = useState(false)
  const [endpoint, setEndpoint] = useState('')
  const [model, setModel] = useState('')

  useEffect(() => {
    if (settings.data) {
      setAiEnabled(settings.data.ai_enabled)
      setEndpoint(settings.data.ai_endpoint)
      setModel(settings.data.ai_model)
    }
  }, [settings.data])

  async function save() {
    try {
      await api.updateSettings({ ai_enabled: aiEnabled, ai_endpoint: endpoint, ai_model: model, theme: themePref })
      notify('Settings saved.', 'success')
      aiStatus.reload()
    } catch (e) { notify((e as Error).message, 'error') }
  }

  if (settings.loading) return <Loading />
  if (settings.error) return <ErrorBox message={settings.error} />

  return (
    <div className="stack" style={{ gap: 20, maxWidth: 680 }}>
      <div><h1>Settings</h1><p className="muted">All settings are stored locally. Nothing is sent to external services.</p></div>

      <Card>
        <CardHead title="Appearance" />
        <div className="card-pad">
          <label className="field"><span>Theme</span>
            <select value={themePref} onChange={(e) => setThemePref(e.target.value as never)}>
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
        </div>
      </Card>

      <Card>
        <CardHead title="Optional local AI (Ollama)"
          sub="Disabled by default. Core analysis is fully deterministic and never requires AI." />
        <div className="card-pad">
          <label className="field" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <input type="checkbox" checked={aiEnabled} onChange={(e) => setAiEnabled(e.target.checked)} style={{ width: 'auto' }} />
            <span style={{ margin: 0 }}>Enable AI explanations via a local Ollama runtime</span>
          </label>
          <label className="field"><span>Local endpoint</span>
            <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="http://localhost:11434" disabled={!aiEnabled} /></label>
          <label className="field"><span>Model</span>
            <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="llama3.2" disabled={!aiEnabled} /></label>

          <div className="small">
            Runtime status:{' '}
            {aiStatus.loading ? 'checking…' : aiStatus.data?.available ? (
              <span className="badge low">reachable</span>
            ) : (
              <span className="badge neutral">{aiStatus.data?.enabled ? 'unreachable (deterministic fallback in use)' : 'disabled'}</span>
            )}
          </div>
          <p className="small muted mt">
            AI only explains existing deterministic findings — it never invents dependencies or evidence,
            and repository source code is never sent to any external API.
          </p>
        </div>
      </Card>

      <button className="btn primary" onClick={save}>Save settings</button>
    </div>
  )
}
