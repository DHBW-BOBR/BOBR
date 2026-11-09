import axios from 'axios'

const BASE_URL = 'http://localhost:8000/api'

export const importFile = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return axios.post(`${BASE_URL}/import/`, formData)
}

export const runValidation = () =>
  axios.post(`${BASE_URL}/validate/`)

export const acceptCorrection = (issueId) =>
  axios.post(`${BASE_URL}/corrections/${issueId}/accept`)

export const rejectCorrection = (issueId) =>
  axios.post(`${BASE_URL}/corrections/${issueId}/reject`)
