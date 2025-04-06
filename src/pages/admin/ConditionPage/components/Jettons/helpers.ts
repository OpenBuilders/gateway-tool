import { ConditionJetton } from '@store'

export const validateJettonAddress = (address: string): boolean => {
  if (!address) return false
  const addressRegex = /^0:[a-fA-F0-9]{64}$/
  return addressRegex.test(address)
}

export const validateAmount = (amount: number): boolean => {
  console.log(amount)
  if (!amount) return false
  return !isNaN(amount) && amount > 0 && amount <= 1000000000
}

export const validateJettonsCondition = (condition: ConditionJetton) => {
  if (!condition) return false

  return (
    validateJettonAddress(condition.address) && validateAmount(condition.amount)
  )
}
