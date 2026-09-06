import { PLACEHOLDER } from '../formConfig.js'

// Short, honest, probability-tiered explanation. Never states certainty.
function explanationFor(riskLevel, probability) {
  const pct = (probability * 100).toFixed(1)
  switch (riskLevel) {
    case 'High':
      return `Based on patterns learned from historical customer data, this customer has a high estimated churn probability (${pct}%). This is a predicted risk, not a certainty.`
    case 'Medium':
      return `Based on patterns learned from historical customer data, this customer shows an elevated estimated churn probability (${pct}%). Consider monitoring or proactive retention.`
    default:
      return `Based on patterns learned from historical customer data, this customer has a low estimated churn probability (${pct}%).`
  }
}

export default function ResultCard({ result, onReset, submitting }) {
  const hasResult = !!result

  if (!hasResult) {
    return (
      <div className="card result-card result-empty" aria-live="polite">
        <h2 className="card-title">Prediction Result</h2>
        <div className="empty-state">
          <div className="empty-icon" aria-hidden="true">📊</div>
          {submitting ? (
            <>
              <p className="empty-title">Evaluating customer…</p>
              <p className="empty-text">Running the profile through the trained model.</p>
            </>
          ) : (
            <>
              <p className="empty-title">
                Enter customer details and click <strong>Predict Churn</strong> to
                see the result.
              </p>
              <p className="empty-text">
                The result will show the estimated churn probability, a risk
                level, and the model&apos;s most influential factors.
              </p>
            </>
          )}
        </div>
      </div>
    )
  }

  const { churn_prediction, churn_probability, risk_level, model_name, top_factors, input_warnings } = result
  const churned = churn_prediction
  const pct = (churn_probability * 100).toFixed(1)

  const riskClass = {
    Low: 'risk-low',
    Medium: 'risk-medium',
    High: 'risk-high',
  }[risk_level] || ''

  return (
    <div className={`card result-card ${churned ? 'result-churn' : 'result-stay'}`}>
      <h2 className="card-title">Prediction Result</h2>

      <div className={`result-badge ${churned ? 'badge-churn' : 'badge-stay'}`}>
        {churned ? '⚠ Likely to Churn' : '✓ Likely to Stay'}
      </div>

      <div className="result-stats">
        <div className="stat">
          <span className="stat-label">Churn Probability</span>
          <span className="stat-value">{pct}%</span>
        </div>
        <div className="stat">
          <span className="stat-label">Risk Level</span>
          <span className={`stat-value risk-pill ${riskClass}`}>{risk_level}</span>
        </div>
      </div>

      <div className="probability-bar" role="img"
           aria-label={`Estimated churn probability ${pct} percent`}>
        <div className="probability-fill" style={{ width: `${pct}%` }} />
        <div className="probability-marker" style={{ left: '40%' }} title="Medium risk threshold (40%)" />
        <div className="probability-marker" style={{ left: '70%' }} title="High risk threshold (70%)" />
      </div>
      <div className="probability-scale">
        <span>0%</span><span>40% (Medium)</span><span>70% (High)</span><span>100%</span>
      </div>

      <p className="result-explanation">{explanationFor(risk_level, churn_probability)}</p>

      {Array.isArray(input_warnings) && input_warnings.length > 0 && (
        <div className="warning-box" role="status">
          <strong>Input warning:</strong>
          <ul>
            {input_warnings.map((w) => (
              <li key={w.field}>{w.message}</li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(top_factors) && top_factors.length > 0 && (
        <div className="factors">
          <h3>Most Influential Factors — Model Wide</h3>
          <p className="factors-note">
            These are global feature-importance results calculated on held-out
            data. They describe which features influence the model overall and
            are <strong>not</strong> a personalized explanation for this
            individual customer.
          </p>
          <ul>
            {top_factors.slice(0, 5).map((f) => (
              <li key={f.feature}>
                <span className="factor-name">
                  {f.feature.replace(/([A-Z])/g, ' $1').trim()}
                </span>
                <span className="factor-bar">
                  <span className="factor-fill"
                        style={{ width: `${Math.min(100, (f.importance / top_factors[0].importance) * 100)}%` }} />
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="model-note">Model: <code>{model_name}</code></p>

      <button className="btn-secondary" type="button" onClick={onReset}>
        Predict Another Customer
      </button>
    </div>
  )
}
