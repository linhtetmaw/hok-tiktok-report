import { useState, useEffect, useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

// Use proxy in dev (no CORS) or full URL if set
const API_URL = import.meta.env.VITE_API_URL || ''
const PASSCODE = 'HOK2026'
const AUTH_KEY = 'tiktok_dashboard_authenticated'

// Find column by possible names (handles different sheet formats)
function findCol(row, candidates) {
  const keys = Object.keys(row || {})
  for (const c of candidates) {
    const found = keys.find((k) => k.toLowerCase().includes(c.toLowerCase()))
    if (found) return found
  }
  return null
}

// Exclude summary/total rows (e.g. "Unknown", "Total", "Sum" from sheet)
function isSummaryRow(row, kolCol) {
  if (!kolCol) return false
  const val = String(row[kolCol] || '').trim().toLowerCase()
  if (!val || val === 'unknown') return true
  if (['total', 'sum', 'grand total', 'subtotal'].some((s) => val.includes(s))) return true
  return false
}

const DATE_PRESETS = [
  { id: 'all', label: 'All time' },
  { id: 'week', label: 'This week' },
  { id: 'month', label: 'This month' },
  { id: 'last7', label: 'Last 7 days' },
  { id: 'last30', label: 'Last 30 days' },
  { id: 'custom', label: 'Custom' },
]

function toDateStr(d) {
  return d.toISOString().slice(0, 10)
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    try {
      return sessionStorage.getItem(AUTH_KEY) === 'true'
    } catch {
      return false
    }
  })
  const [passcodeInput, setPasscodeInput] = useState('')
  const [passcodeError, setPasscodeError] = useState(false)
  const [data, setData] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [datePreset, setDatePreset] = useState('all')

  function handlePasscodeSubmit(e) {
    e.preventDefault()
    setPasscodeError(false)
    if (passcodeInput.trim() === PASSCODE) {
      try {
        sessionStorage.setItem(AUTH_KEY, 'true')
      } catch {}
      setIsAuthenticated(true)
      setPasscodeInput('')
    } else {
      setPasscodeError(true)
    }
  }
  const [customStart, setCustomStart] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    return toDateStr(d)
  })
  const [customEnd, setCustomEnd] = useState(() => toDateStr(new Date()))

  async function fetchData() {
    setLoading(true)
    setError(null)
    try {
      const url = API_URL ? `${API_URL}/api/data` : '/api/data'
      const res = await fetch(url)
      const text = await res.text()
      let json
      try {
        json = text ? JSON.parse(text) : {}
      } catch {
        setError(
          `API returned invalid JSON (status ${res.status}). ` +
            (res.status === 404
              ? 'Set VITE_API_URL to your Railway backend URL in Vercel and redeploy, or run the API locally on port 8000.'
              : 'The API may have crashed or returned an error.')
        )
        setData([])
        return
      }
      if (!res.ok) {
        setError(json.detail || json.error || `API error: ${res.status}`)
        setData([])
      } else if (json.error) {
        setError(json.error)
        setData([])
      } else {
        setData(json.rows || [])
        setLastUpdated(json.last_updated)
      }
    } catch (err) {
      setError(
        err.message === 'Failed to fetch'
          ? 'Could not connect to API. Make sure the API is running (Terminal 1: uvicorn main:app --reload --port 8000).'
          : err.message || 'Failed to load data'
      )
      setData([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const columns = data.length > 0 ? Object.keys(data[0]) : []
  const sampleRow = data[0] || {}

  const kolCol = findCol(sampleRow, ['kol_name', 'kol', 'creator'])
  const engagementCol = findCol(sampleRow, ['engagement', 'engagements'])
  const playsCol = findCol(sampleRow, ['total_plays', 'plays', 'views'])
  const dateCol = findCol(sampleRow, ['date', 'posted_date', 'publish_date'])

  const filteredData = useMemo(() => {
    return data.filter((r) => !isSummaryRow(r, kolCol))
  }, [data, kolCol])

  const dateFilteredData = useMemo(() => {
    if (datePreset === 'all') return filteredData
    if (!dateCol) return filteredData
    const now = new Date()
    let startDate, endDate
    if (datePreset === 'custom') {
      startDate = new Date(customStart)
      startDate.setHours(0, 0, 0, 0)
      endDate = new Date(customEnd)
      endDate.setHours(23, 59, 59, 999)
    } else {
      switch (datePreset) {
        case 'week':
          startDate = new Date(now)
          startDate.setDate(now.getDate() - now.getDay())
          startDate.setHours(0, 0, 0, 0)
          break
        case 'month':
          startDate = new Date(now.getFullYear(), now.getMonth(), 1)
          break
        case 'last7':
          startDate = new Date(now)
          startDate.setDate(now.getDate() - 7)
          startDate.setHours(0, 0, 0, 0)
          break
        case 'last30':
          startDate = new Date(now)
          startDate.setDate(now.getDate() - 30)
          startDate.setHours(0, 0, 0, 0)
          break
        default:
          return filteredData
      }
      endDate = new Date(now)
      endDate.setHours(23, 59, 59, 999)
    }
    return filteredData.filter((r) => {
      const val = r[dateCol]
      if (val == null || val === '') return false
      const d = new Date(val)
      if (isNaN(d.getTime())) return false
      return d >= startDate && d <= endDate
    })
  }, [filteredData, dateCol, datePreset, customStart, customEnd])

  const totalPost = dateFilteredData.length
  const totalEngagement = useMemo(() => {
    if (!engagementCol) return 0
    return dateFilteredData.reduce((sum, r) => sum + (Number(r[engagementCol]) || 0), 0)
  }, [dateFilteredData, engagementCol])
  const totalPlays = useMemo(() => {
    if (!playsCol) return 0
    return dateFilteredData.reduce((sum, r) => sum + (Number(r[playsCol]) || 0), 0)
  }, [dateFilteredData, playsCol])

  const engagementByKol = useMemo(() => {
    if (!kolCol || !engagementCol) return []
    const map = {}
    dateFilteredData.forEach((r) => {
      const name = (r[kolCol] || '').trim() || 'Unknown'
      if (name === 'Unknown') return
      map[name] = (map[name] || 0) + (Number(r[engagementCol]) || 0)
    })
    return Object.entries(map)
      .map(([name, value]) => ({ name, engagement: value }))
      .sort((a, b) => b.engagement - a.engagement)
  }, [dateFilteredData, kolCol, engagementCol])

  const playsByKol = useMemo(() => {
    if (!kolCol || !playsCol) return []
    const map = {}
    dateFilteredData.forEach((r) => {
      const name = (r[kolCol] || '').trim() || 'Unknown'
      if (name === 'Unknown') return
      map[name] = (map[name] || 0) + (Number(r[playsCol]) || 0)
    })
    return Object.entries(map)
      .map(([name, plays]) => ({ name, plays }))
      .sort((a, b) => b.plays - a.plays)
  }, [dateFilteredData, kolCol, playsCol])

  const chartStyle = {
    background: '#1e293b',
    borderRadius: '8px',
    padding: '1rem',
    marginBottom: '1.5rem',
  }

  if (!isAuthenticated) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0f172a',
          padding: '2rem',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            marginBottom: '1.5rem',
            minHeight: '80px',
            alignItems: 'center',
            overflow: 'hidden',
          }}
        >
          <img
            src="/reindeers-web-logo.png"
            alt="Reindeers logo"
            style={{
              maxWidth: '200px',
              maxHeight: '80px',
              objectFit: 'contain',
            }}
            onError={(e) => {
              e.target.style.display = 'none'
            }}
          />
        </div>
        <div
          style={{
            background: '#1e293b',
            borderRadius: '12px',
            padding: '2.5rem',
            border: '1px solid #334155',
            minWidth: '320px',
          }}
        >
          <h1 style={{ margin: '0 0 0.5rem', fontSize: '1.25rem', color: '#00F88D' }}>
            HOK TikTok KOLs Dashboard
          </h1>
          <p style={{ margin: '0 0 1.5rem', color: '#94a3b8', fontSize: '0.9rem' }}>
            Enter passcode to continue
          </p>
          <form onSubmit={handlePasscodeSubmit}>
            <input
              type="password"
              value={passcodeInput}
              onChange={(e) => {
                setPasscodeInput(e.target.value)
                setPasscodeError(false)
              }}
              placeholder="Passcode"
              autoFocus
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                fontSize: '1rem',
                background: '#0f172a',
                border: `1px solid ${passcodeError ? '#dc2626' : '#334155'}`,
                borderRadius: '6px',
                color: '#f8fafc',
                boxSizing: 'border-box',
              }}
            />
            {passcodeError && (
              <p style={{ margin: '0.5rem 0 0', color: '#f87171', fontSize: '0.875rem' }}>
                Incorrect Passcode
              </p>
            )}
            <button
              type="submit"
              style={{
                marginTop: '1.25rem',
                width: '100%',
                padding: '0.75rem',
                fontSize: '1rem',
                fontWeight: 500,
                background: '#00F88D',
                color: '#0f172a',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Enter
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.75rem', color: '#00F88D' }}>HOK TikTok KOLs Engagement Dashboard</h1>
        <p style={{ margin: '0.5rem 0 0', color: '#94a3b8', fontSize: '0.9rem' }}>
          Powered by Reindeers Agency.
        </p>
      </header>

      <div style={{ marginBottom: '1.5rem', display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ color: '#94a3b8', fontSize: '0.9rem', marginRight: '0.25rem' }}>Date range:</span>
          {DATE_PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => setDatePreset(p.id)}
              style={{
                padding: '0.4rem 0.75rem',
                background: datePreset === p.id ? '#3b82f6' : '#334155',
                color: '#f8fafc',
                border: '1px solid #475569',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.85rem',
              }}
            >
              {p.label}
            </button>
          ))}
          {datePreset === 'custom' && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginLeft: '0.5rem' }}>
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                style={{
                  padding: '0.4rem 0.5rem',
                  background: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: '#f8fafc',
                  fontSize: '0.9rem',
                }}
              />
              <span style={{ color: '#64748b' }}>to</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                style={{
                  padding: '0.4rem 0.5rem',
                  background: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: '#f8fafc',
                  fontSize: '0.9rem',
                }}
              />
            </span>
          )}
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          style={{
            padding: '0.5rem 1rem',
            background: '#334155',
            color: '#f8fafc',
            border: '1px solid #475569',
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '0.9rem',
          }}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
        {lastUpdated && (
          <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
            Last updated: {new Date(lastUpdated).toLocaleString()}
          </span>
        )}
      </div>

      {error && (
        <div
          style={{
            padding: '1rem',
            background: '#7f1d1d',
            color: '#fecaca',
            borderRadius: '6px',
            marginBottom: '1rem',
          }}
        >
          {error}
        </div>
      )}

      {loading && data.length === 0 ? (
        <p style={{ color: '#94a3b8' }}>Loading data…</p>
      ) : data.length === 0 ? (
        <p style={{ color: '#94a3b8' }}>No data to display.</p>
      ) : (
        <>
          {/* KPI Widgets */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '1rem',
              marginBottom: '2rem',
            }}
          >
            <div
              style={{
                ...chartStyle,
                textAlign: 'center',
              }}
            >
              <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Total Post
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{totalPost.toLocaleString()}</div>
            </div>
            <div
              style={{
                ...chartStyle,
                textAlign: 'center',
              }}
            >
              <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Total Engagement
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>
                {totalEngagement.toLocaleString()}
              </div>
            </div>
            <div
              style={{
                ...chartStyle,
                textAlign: 'center',
              }}
            >
              <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Total Plays
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>
                {totalPlays.toLocaleString()}
              </div>
            </div>
          </div>

          {/* Bar chart: Total Engagement by KOL Name */}
          {engagementByKol.length > 0 && (
            <div style={chartStyle}>
              <h3 style={{ margin: '0 0 1rem', fontSize: '1rem' }}>
                Total Engagement
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={engagementByKol} margin={{ top: 5, right: 20, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155' }}
                    labelStyle={{ color: '#f8fafc' }}
                    formatter={(value) => [value.toLocaleString(), 'Engagement']}
                  />
                  <Bar dataKey="engagement" fill="#3b82f6" name="Engagement" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Bar chart: Total Video Plays by KOL Name */}
          {playsByKol.length > 0 && (
            <div style={chartStyle}>
              <h3 style={{ margin: '0 0 1rem', fontSize: '1rem' }}>
                Total Video Plays
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={playsByKol} margin={{ top: 5, right: 20, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155' }}
                    labelStyle={{ color: '#f8fafc' }}
                    formatter={(value) => [value.toLocaleString(), 'Plays']}
                  />
                  <Bar dataKey="plays" fill="#10b981" name="Plays" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Scrollable table at bottom - all headers */}
          <div style={{ marginTop: '2rem' }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1rem' }}>
              All Data (scroll horizontally to see all columns)
            </h3>
            <div
              style={{
                overflowX: 'auto',
                overflowY: 'visible',
                border: '1px solid #334155',
                borderRadius: '8px',
                background: '#1e293b',
              }}
            >
              <table
                style={{
                  width: 'max-content',
                  minWidth: '100%',
                  borderCollapse: 'collapse',
                }}
              >
                <thead>
                  <tr>
                    {columns.map((col) => (
                      <th
                        key={col}
                        style={{
                          padding: '0.75rem 1rem',
                          textAlign: 'left',
                          background: '#334155',
                          color: '#94a3b8',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          textTransform: 'capitalize',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {col.replace(/_/g, ' ')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dateFilteredData.map((row, i) => (
                    <tr
                      key={i}
                      style={{
                        borderBottom: '1px solid #334155',
                      }}
                    >
                      {columns.map((col) => (
                        <td
                          key={col}
                          style={{
                            padding: '0.75rem 1rem',
                            fontSize: '0.9rem',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {row[col] != null ? String(row[col]) : '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default App
