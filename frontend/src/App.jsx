import { useState } from 'react'
import ChurnForm from './components/ChurnForm.jsx'
import ResultCard from './components/ResultCard.jsx'
import ModelPanel from './components/ModelPanel.jsx'
import { fetchModelInfo, fetchPrediction } from './api.js'
import { INITIAL_FORM, REQUIRED_SELECTS } from './formConfig.js'

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
    <div className="app">
      <header className="app-header">
        <h1>Telecom Customer Churn Prediction</h1>
        <p className="app-subtitle">
          Enter a customer&apos;s profile to estimate how likely they are to
          cancel their service. A machine-learning model — trained on 7,043
          historical customer records — returns an estimated churn
          probability and a Low / Medium / High risk rating to help prioritize
          retention efforts.
        </p>
      </header>

      {apiError && (
        <div className="alert alert-error" role="alert">
          <strong>Error:</strong> {apiError}
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

      <footer className="app-footer">
        Predictions are statistical estimates from historical data — not guarantees.
        Charges are in US dollars, matching the original dataset.
      </footer>
    </div>
  )
}
