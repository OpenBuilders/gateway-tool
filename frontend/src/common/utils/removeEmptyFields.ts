export const removeEmptyFields = (obj: Record<string, any>) => {
  return Object.fromEntries(
    Object.entries(obj).filter(([_, value]) => {
      if (value === undefined) return false
      if (value === null) return true
      if (typeof value === 'string' && value.trim() === '') return false
      if (Array.isArray(value) && value.length === 0) return false
      if (typeof value === 'object' && Object.keys(value).length === 0)
        return false
      return true
    })
  )
}
