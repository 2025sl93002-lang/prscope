// Report tab — live Markdown preview + exports. SPDX-License-Identifier: MIT
import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { useToast } from '../../components/Toast'
import { Card, CardHead, ErrorBox, Loading } from '../../components/ui'

export default function Report({ analysisId }: { analysisId: number }) {
  const { notify } = useToast()
  const md = useAsync(
    () => fetch(api.reportUrl(analysisId, 'md')).then((r) => {
      if (!r.ok) throw new Error(`Failed to load report (${r.status})`)
      return r.text()
    }),
    [analysisId],
  )
  const [downloading, setDownloading] = useState('')

  async function download(fmt: 'md' | 'json' | 'html') {
    setDownloading(fmt)
    try {
      const resp = await fetch(api.reportUrl(analysisId, fmt))
      if (!resp.ok) throw new Error(`${resp.status}`)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `prscope-report-${analysisId}.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
      notify(`Downloaded ${fmt.toUpperCase()} report.`, 'success')
    } catch (e) {
      notify(`Download failed: ${(e as Error).message}`, 'error')
    } finally { setDownloading('') }
  }

  return (
    <Card>
      <CardHead
        title="Verification report"
        sub="Generated from real analysis results — no placeholders."
        right={
          <div className="btn-group">
            <button className="btn sm" onClick={() => download('md')} disabled={!!downloading}>⤓ Markdown</button>
            <button className="btn sm" onClick={() => download('json')} disabled={!!downloading}>⤓ JSON</button>
            <button className="btn sm" onClick={() => window.open(api.reportUrl(analysisId, 'html'), '_blank')}>↗ HTML</button>
          </div>
        }
      />
      <div className="card-pad">
        {md.loading ? <Loading /> : md.error ? <ErrorBox message={md.error} /> : (
          <div className="report-md" style={{ maxWidth: 820 }}>
            <Markdown remarkPlugins={[remarkGfm]}>{md.data || ''}</Markdown>
          </div>
        )}
      </div>
    </Card>
  )
}
