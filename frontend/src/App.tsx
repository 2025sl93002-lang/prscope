// Routes. SPDX-License-Identifier: MIT
import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import Dashboard from './pages/Dashboard'
import Repositories from './pages/Repositories'
import Analyses from './pages/Analyses'
import AnalysisDetail from './pages/AnalysisDetail'
import Settings from './pages/Settings'
import About from './pages/About'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout crumbs={<b>Dashboard</b>}><Dashboard /></Layout>} />
      <Route path="/repositories" element={<Layout crumbs={<b>Repositories</b>}><Repositories /></Layout>} />
      <Route path="/analyses" element={<Layout crumbs={<b>Analyses</b>}><Analyses /></Layout>} />
      <Route path="/analyses/:id" element={<AnalysisDetail />} />
      <Route path="/analyses/:id/:tab" element={<AnalysisDetail />} />
      <Route path="/settings" element={<Layout crumbs={<b>Settings</b>}><Settings /></Layout>} />
      <Route path="/about" element={<Layout crumbs={<b>About / Open Source</b>}><About /></Layout>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
