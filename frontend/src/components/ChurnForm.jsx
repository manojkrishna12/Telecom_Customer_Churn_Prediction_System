import { SECTIONS } from '../formConfig.js'
import { PLACEHOLDER } from '../formConfig.js'

export default function ChurnForm({
  values, errors, submitting, onChange, onSubmit,
}) {
  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit()
  }

  return (
    <form className="card churn-form" onSubmit={handleSubmit}>
      <h2 className="card-title">Customer Input</h2>
      <p className="card-subtitle">
        All fields are required. Choose values that describe the customer.
      </p>

      {SECTIONS.map((section) => (
        <fieldset className="form-section" key={section.title}>
          <legend>{section.title}</legend>
          <div className="field-grid">
            {section.fields.map((field) => (
              <div className={`field ${errors[field.name] ? 'field-error' : ''}`} key={field.name}>
                <label htmlFor={field.name}>{field.label}</label>
                {field.type === 'select' ? (
                  <select
                    id={field.name}
                    name={field.name}
                    value={values[field.name]}
                    onChange={(e) => onChange(field.name, e.target.value)}
                    className={values[field.name] === PLACEHOLDER ? 'is-placeholder' : ''}
                  >
                    {field.placeholder && (
                      <option value={PLACEHOLDER} disabled>
                        {field.placeholder}
                      </option>
                    )}
                    {field.options.map((opt) => (
                      <option key={opt} value={opt}>
                        {field.optionLabels?.[opt] ?? opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    id={field.name}
                    name={field.name}
                    type="number"
                    min={field.min}
                    max={field.max}
                    step={field.step}
                    placeholder={field.placeholder}
                    value={values[field.name]}
                    onChange={(e) => onChange(field.name, e.target.value)}
                  />
                )}
                {errors[field.name] && (
                  <span className="field-error-msg">{errors[field.name]}</span>
                )}
              </div>
            ))}
          </div>
        </fieldset>
      ))}

      <button className="btn-predict" type="submit" disabled={submitting}>
        {submitting ? (
          <>
            <span className="spinner" aria-hidden="true" />
            Predicting…
          </>
        ) : (
          'Predict Churn'
        )}
      </button>
    </form>
  )
}
