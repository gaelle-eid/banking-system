export const SPENDING_CATEGORIES = [
  { value: 'dining', label: 'Dining & Restaurants', icon: '🍽️' },
  { value: 'groceries', label: 'Groceries', icon: '🛒' },
  { value: 'travel', label: 'Travel', icon: '✈️' },
  { value: 'entertainment', label: 'Entertainment', icon: '🎬' },
  { value: 'bills_utilities', label: 'Bills & Utilities', icon: '🧾' },
  { value: 'shopping', label: 'Shopping', icon: '🛍️' },
  { value: 'healthcare', label: 'Healthcare', icon: '🏥' },
  { value: 'other', label: 'Other', icon: '📦' },
]

// Includes system-assigned categories too, for display purposes (history, charts)
export const ALL_CATEGORIES = {
  dining: { label: 'Dining & Restaurants', icon: '🍽️' },
  groceries: { label: 'Groceries', icon: '🛒' },
  travel: { label: 'Travel', icon: '✈️' },
  entertainment: { label: 'Entertainment', icon: '🎬' },
  bills_utilities: { label: 'Bills & Utilities', icon: '🧾' },
  shopping: { label: 'Shopping', icon: '🛍️' },
  healthcare: { label: 'Healthcare', icon: '🏥' },
  transfer_to_person: { label: 'Sent to Someone', icon: '👤' },
  cash_withdrawal: { label: 'Cash Withdrawal', icon: '💵' },
  income: { label: 'Income', icon: '💰' },
  loan_repayment: { label: 'Loan Repayment', icon: '🏦' },
  savings: { label: 'Savings', icon: '🐷' },
  other: { label: 'Other', icon: '📦' },
}

export function categoryLabel(value) {
  return ALL_CATEGORIES[value]?.label || 'Other'
}

export function categoryIcon(value) {
  return ALL_CATEGORIES[value]?.icon || '📦'
}