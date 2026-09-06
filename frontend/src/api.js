// API base URL: set VITE_API_BASE_URL for production builds (deployed HTTPS
// backend), or VITE_API_URL in older .env files. Falls back to the local dev
// server. This keeps localhost out of the production bundle.
const API_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000'

export async function fetchHealth(signal) {
  const res = await fetch(`${API_URL}/health`, { signal })
  if (!res.ok) throw new Error(`API responded with status ${res.status}`)
  return res.json()
}

export async function fetchModelInfo(signal) {
  const res = await fetch(`${API_URL}/model-info`, { signal })
  if (!res.ok) throw new Error(`API responded with status ${res.status}`)
  return res.json()
}

export async function fetchPrediction(payload, signal) {
  let res
  try {
    res = await fetch(`${API_URL}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw new Error(
      `Cannot reach the prediction API at ${API_URL}. ` +
      'Make sure the backend is running (uvicorn app.main:app --port 8000).'
    )
  }

  let body = null
  try {
    body = await res.json()
  } catch {
    throw new Error(`API returned a non-JSON response (status ${res.status}).`)
  }

  if (!res.ok) {
    // FastAPI validation errors: array of {loc, msg, type}
    if (Array.isArray(body.detail)) {
      const problems = body.detail
        .map((d) => `${d.loc?.slice(1).join('.') || 'input'}: ${d.msg}`)
        .join('; ')
      throw new Error(`Validation failed - ${problems}`)
    }
    throw new Error(body.detail || `API error (status ${res.status}).`)
  }

  return body
}
