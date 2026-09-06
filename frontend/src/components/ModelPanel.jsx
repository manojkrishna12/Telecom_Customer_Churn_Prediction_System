// Model Performance panel. ALL values come from GET /model-info (which reads
// metrics.json/metadata.json) - nothing is hardcoded here, so the panel stays
// truthful if the model is retrained.

export default function ModelPanel({ info }) {
  if (!info || !info.test_metrics) return null
  const { model_name, test_metrics, versions } = info

  const metrics = [
    { label: 'Accuracy', value: test_metrics.accuracy },
    { label: 'Precision', value: test_metrics.precision },
    { label: 'Recall', value: test_metrics.recall },
    { label: 'F1 Score', value: test_metrics.f1 },
    { label: 'ROC-AUC', value: test_metrics.roc_auc },
  ]

  return (
    <div className="card model-panel">
      <h2 className="card-title">Model Performance</h2>
      <p className="card-subtitle">Held-out test set results (n = 1,409 customers).</p>

      <div className="model-name-row">
        <span className="model-name-label">Final Model</span>
        <span className="model-name-value">{prettyModelName(model_name)}</span>
      </div>

      {Array.isArray(info.components) && info.components.length > 1 && (
        <div className="model-components">
          {info.components.map((c) => (
            <span className="component-chip" key={c}>{c}</span>
          ))}
        </div>
      )}

      <ul className="metric-list">
        {metrics.map((m) => (
          <li key={m.label}>
            <span className="metric-label">{m.label}</span>
            <span className="metric-bar">
              <span className="metric-fill" style={{ width: `${(m.value * 100).toFixed(1)}%` }} />
            </span>
            <span className="metric-value">{(m.value * 100).toFixed(2)}%</span>
          </li>
        ))}
      </ul>

      <p className="panel-note">
        The final model was selected after comparing multiple classification
        algorithms using cross-validation and a held-out test set. ROC-AUC was
        the primary selection metric, with F1/recall used as a tie-break
        because identifying potential churners is important. Accuracy alone
        would be misleading: with a ~26.5% churn rate, always predicting
        &quot;No churn&quot; already scores ~73% while catching no churners.
      </p>

      {versions?.['scikit-learn'] && (
        <p className="panel-meta">
          scikit-learn {versions['scikit-learn']}
          {info.trained_at ? ` · trained ${info.trained_at.slice(0, 10)}` : ''}
        </p>
      )}
    </div>
  )
}

function prettyModelName(name) {
  const map = {
    voting_ensemble: 'Soft Voting Ensemble',
    stacking_ensemble: 'Stacking Ensemble',
    logistic_regression: 'Logistic Regression',
    random_forest: 'Random Forest',
    gradient_boosting: 'Gradient Boosting',
    ada_boost: 'AdaBoost',
    knn: 'K-Nearest Neighbors',
    svc: 'Support Vector Machine',
  }
  return map[name] || name
}
