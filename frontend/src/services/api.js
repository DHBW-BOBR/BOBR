/**
 * api.js — Zentraler Service für alle HTTP-Anfragen ans FastAPI-Backend.
 * Basis-URL: http://localhost:8000/api
 */
import axios from 'axios'

const BASE_URL = 'http://localhost:8000/api'

/**
 * Lädt eine Literaturdatei ins Backend hoch.
 * @param {File} file - Datei (.bib, .txt oder .pdf)
 * @returns {Promise} Axios-Response mit den geparsten Einträgen
 */
export const importFile = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return axios.post(`${BASE_URL}/import/`, formData)
}

/**
 * Startet die Prüfung der importierten Literaturdaten.
 * @returns {Promise} Axios-Response mit der Liste der gefundenen Probleme
 */
export const runValidation = () =>
  axios.post(`${BASE_URL}/validate/`)

/**
 * Nimmt einen Korrekturvorschlag an.
 * @param {number} issueId - ID des Problems
 * @returns {Promise} Axios-Response
 */
export const acceptCorrection = (issueId) =>
  axios.post(`${BASE_URL}/corrections/${issueId}/accept`)

/**
 * Lehnt einen Korrekturvorschlag ab.
 * @param {number} issueId - ID des Problems
 * @returns {Promise} Axios-Response
 */
export const rejectCorrection = (issueId) =>
  axios.post(`${BASE_URL}/corrections/${issueId}/reject`)
