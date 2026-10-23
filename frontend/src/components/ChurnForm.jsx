import { useState } from 'react'
import { SECTIONS } from '../formConfig.js'
import { PLACEHOLDER } from '../formConfig.js'
import { UserIcon, GearIcon, CardIcon, ChevronIcon, BoltIcon } from './Icons.jsx'

const SECTION_ICONS = {
  Demographics: UserIcon,
  Services: GearIcon,
  'Account & Billing': CardIcon,
}

export default function ChurnForm({
  values, errors, submitting, onChange, onSubmit,
}) {
  // Sections start expanded; the chevron toggles them without touching state.
  const [open, setOpen] = useState(() => SECTIONS.map(() => true))
  const toggle = (i) => setOpen((prev) => prev.map((v, j) => (j === i ? !v : v)))

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit()
  }

  return (
    <form className="card churn-form" onSubmit={handleSubmit}>
      <div className="card-head">
        <div className="card-icon" aria-hidden="true"><UserIcon /></div>
        <div>
          <h2 className="card-title">Customer Information</h2>
          <p className="card-subtitle">
            Enter the customer details below to predict the likelihood of churn.
          </p>
        </div>
      </div>

      {SECTIONS.map((section, i) => {
        const SectionIcon = SECTION_ICONS[section.title] || UserIcon
        const isOpen = open[i]
        return (
          <section className="form-section" key={section.title}>
            <button
              type="button"
              className="section-head"
              aria-expanded={isOpen}
              onClick={() => toggle(i)}
            >
              <SectionIcon />
              <span>{section.title}</span>
              <ChevronIcon className={`chev${isOpen ? '' : ' down'}`} />
            </button>
            {isOpen && (
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
            )}
          </section>
        )
      })}

      <button className="btn-predict" type="submit" disabled={submitting}>
        {submitting ? (
          <>
            <span className="spinner" aria-hidden="true" />
            Predicting…
          </>
        ) : (
          <>
            <BoltIcon />
            Predict Churn
          </>
        )}
      </button>
    </form>
  )
}
