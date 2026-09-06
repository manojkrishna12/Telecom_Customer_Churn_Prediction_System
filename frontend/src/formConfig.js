// All field metadata lives here: names, types, dropdown options.
// The option values are exactly the categories the model was trained on,
// mirroring ml/prepare_data.py and backend/app/schemas.py.

const YES_NO = ['Yes', 'No']
const ADDON = ['Yes', 'No', 'No internet service']

// Placeholder marker: fields with `placeholder` do NOT preselect a value.
// The user must choose explicitly, and App.jsx validates those fields.
export const PLACEHOLDER = '__placeholder__'

export const SECTIONS = [
  {
    title: 'Demographics',
    fields: [
      { name: 'gender', label: 'Gender', type: 'select', placeholder: 'Select Gender',
        options: ['Male', 'Female'] },
      { name: 'SeniorCitizen', label: 'Senior Citizen', type: 'select', options: ['0', '1'],
        optionLabels: { '0': 'No', '1': 'Yes' } },
      { name: 'Partner', label: 'Partner', type: 'select', options: YES_NO },
      { name: 'Dependents', label: 'Dependents', type: 'select', options: YES_NO },
    ],
  },
  {
    title: 'Services',
    fields: [
      { name: 'PhoneService', label: 'Phone Service', type: 'select', options: YES_NO },
      { name: 'MultipleLines', label: 'Multiple Lines', type: 'select',
        options: ['No', 'Yes', 'No phone service'] },
      { name: 'InternetService', label: 'Internet Service', type: 'select',
        options: ['DSL', 'Fiber optic', 'No'] },
      { name: 'OnlineSecurity', label: 'Online Security', type: 'select', options: ADDON },
      { name: 'OnlineBackup', label: 'Online Backup', type: 'select', options: ADDON },
      { name: 'DeviceProtection', label: 'Device Protection', type: 'select', options: ADDON },
      { name: 'TechSupport', label: 'Tech Support', type: 'select', options: ADDON },
      { name: 'StreamingTV', label: 'Streaming TV', type: 'select', options: ADDON },
      { name: 'StreamingMovies', label: 'Streaming Movies', type: 'select', options: ADDON },
    ],
  },
  {
    title: 'Account & Billing',
    fields: [
      { name: 'Contract', label: 'Contract', type: 'select', placeholder: 'Select Contract',
        options: ['Month-to-month', 'One year', 'Two year'] },
      { name: 'PaperlessBilling', label: 'Paperless Billing', type: 'select', options: YES_NO },
      { name: 'PaymentMethod', label: 'Payment Method', type: 'select',
        placeholder: 'Select Payment Method',
        options: ['Electronic check', 'Mailed check', 'Bank transfer (automatic)',
                  'Credit card (automatic)'] },
      { name: 'tenure', label: 'Tenure (months)', type: 'number',
        min: 0, max: 600, step: 1, placeholder: 'e.g. 29' },
      { name: 'MonthlyCharges', label: 'Monthly Charges ($)', type: 'number',
        min: 0, max: 100000, step: 0.05, placeholder: 'e.g. 70.70' },
      { name: 'TotalCharges', label: 'Total Charges ($)', type: 'number',
        min: 0, max: 1000000, step: 0.01, placeholder: 'e.g. 1397.48' },
    ],
  },
]

export const INITIAL_FORM = SECTIONS.flatMap((s) => s.fields).reduce((acc, f) => {
  if (f.type === 'number') {
    acc[f.name] = ''
  } else if (f.placeholder) {
    acc[f.name] = PLACEHOLDER
  } else if (f.name === 'SeniorCitizen') {
    acc[f.name] = '0'
  } else {
    acc[f.name] = f.options[0]
  }
  return acc
}, {})

// Fields the user must set explicitly before predicting.
export const REQUIRED_SELECTS = SECTIONS.flatMap((s) => s.fields)
  .filter((f) => f.type === 'select' && f.placeholder)
  .map((f) => ({ name: f.name, label: f.label }))
