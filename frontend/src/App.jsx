import { useState } from 'react'
import ChurnForm from './components/ChurnForm.jsx'
import ResultCard from './components/ResultCard.jsx'
import ModelPanel from './components/ModelPanel.jsx'
import { API_URL, fetchModelInfo, fetchPrediction } from './api.js'
import { INITIAL_FORM, REQUIRED_SELECTS } from './formConfig.js'
import {
  AntennaIcon,
  HomeIcon,
  InfoIcon,
  ChartIcon,
  DocIcon,
} from './components/Icons.jsx'

// Client-side validation mirrors the backend contract (backend/app/schemas.py).
// Caps here are physical sanity limits, not training-range limits - values
// outside the training distribution are allowed and trigger a warning.
const NUMERIC_RULES = {
  tenure: { min: 0, max: 600, label: 'Tenure' },
  MonthlyCharges: { min: 0, max: 100000, label: 'Monthly Charges' },
  TotalCharges: { min: 0, max: 1000000, label: 'Total Charges' },
}

function validate(values) {
  const errors = {}

  for (const { name, label } of REQUIRED_SELECTS) {
    if (!values[name] || values[name] === '__placeholder__') {
      errors[name] = `${label} is required - please make a selection.`
    }
  }

  for (const [name, rule] of Object.entries(NUMERIC_RULES)) {
    const raw = String(values[name]).trim()
    if (raw === '') {
      errors[name] = `${rule.label} is required.`
      continue
    }
    const num = Number(raw)
    if (Number.isNaN(num)) {
      errors[name] = `${rule.label} must be a number.`
    } else if (num < rule.min) {
      errors[name] = `${rule.label} cannot be negative.`
    } else if (num > rule.max) {
      errors[name] = `${rule.label} must be at most ${rule.max.toLocaleString()}.`
    }
  }

  const monthly = Number(values.MonthlyCharges)
  const total = Number(values.TotalCharges)
  if (!errors.MonthlyCharges && !errors.TotalCharges && total < monthly) {
    errors.TotalCharges = 'Total Charges cannot be lower than Monthly Charges.'
  }

  return errors
}

export default function App() {
  const [values, setValues] = useState(INITIAL_FORM)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [apiError, setApiError] = useState(null)
  const [result, setResult] = useState(null)
  // Model info loads once for the Model Performance panel; failures are
  // non-fatal (the panel just does not render).
  const [modelInfo, setModelInfo] = useState(null)

  if (modelInfo === null && !App._modelInfoFailed) {
    fetchModelInfo()
      .then(setModelInfo)
      .catch(() => { App._modelInfoFailed = true })
  }

  const handleChange = (name, value) => {
    setValues((prev) => ({ ...prev, [name]: value }))
    setErrors((prev) => (prev[name] ? { ...prev, [name]: undefined } : prev))
  }

  const handleSubmit = async () => {
    setApiError(null)
    setResult(null)

    const validationErrors = validate(values)
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors)
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        ...values,
        SeniorCitizen: Number(values.SeniorCitizen),
        tenure: Number(values.tenure),
        MonthlyCharges: Number(values.MonthlyCharges),
        TotalCharges: Number(values.TotalCharges),
      }
      const data = await fetchPrediction(payload)
      setResult(data)
    } catch (err) {
      setApiError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const reset = () => {
    setResult(null)
    setApiError(null)
    setErrors({})
  }

  return (
    <div className="app" id="top">
      <header className="app-header">
        <div className="header-inner">
          <div className="brand">
            <div className="brand-icon"><AntennaIcon size={24} /></div>
            <div className="brand-text">
              <h1>Telecom Customer Churn Prediction</h1>
              <p>Predict customer churn and identify high-risk customers</p>
            </div>
          </div>
          <nav className="app-nav" aria-label="Main navigation">
            <a className="nav-pill is-active" href="#top"><HomeIcon /><span>Home</span></a>
            <a className="nav-pill" href="#about"><InfoIcon /><span>About</span></a>
            <a className="nav-pill" href="#model-performance"><ChartIcon /><span>Model Info</span></a>
            <a className="nav-pill" href={`${API_URL}/docs`} target="_blank" rel="noreferrer">
              <DocIcon /><span>Documentation</span>
            </a>
          </nav>
        </div>
      </header>

      {apiError && (
        <div className="app-alert">
          <div className="alert alert-error" role="alert">
            <strong>Error:</strong> {apiError}
          </div>
        </div>
      )}

      <main className="dashboard">
        <section className="dashboard-col" aria-label="Customer input">
          <ChurnForm
            values={values}
            errors={errors}
            submitting={submitting}
            onChange={handleChange}
            onSubmit={handleSubmit}
          />
        </section>

        <section className="dashboard-col" aria-label="Prediction result and model information">
          <ResultCard result={result} onReset={reset} submitting={submitting} />
          {modelInfo && <ModelPanel info={modelInfo} />}
        </section>
      </main>

      <footer className="app-footer" id="about">
        Predictions are statistical estimates from historical data — not guarantees.
        Charges are in US dollars, matching the original dataset.
      </footer>
    </div>
  )
}
