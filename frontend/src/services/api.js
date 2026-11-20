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
 * Ohne uploadId prüft das Backend den zuletzt hochgeladenen Upload,
 * mit uploadId genau diese gespeicherte Prüfung.
 * Warum zwei Varianten: Ohne Parameter bleibt der bisherige Aufruf unverändert,
 * mit Parameter kann eine ältere Prüfung (z. B. nach einem Neustart) erneut geprüft werden.
 * @param {number} [uploadId] - ID der gespeicherten Prüfung (optional)
 * @returns {Promise} Axios-Response mit der Liste der neu gefundenen Probleme
 */
export const runValidation = (uploadId) =>
  uploadId == null
    ? axios.post(`${BASE_URL}/validate/`)
    : axios.post(`${BASE_URL}/validate/`, null, { params: { upload_id: uploadId } })

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

/**
 * @typedef {Object} UploadSummary
 * @property {number} id - ID der gespeicherten Prüfung
 * @property {string} file_name - Name der hochgeladenen Datei
 * @property {'bib'|'txt'|'pdf'} format - Dateiformat
 * @property {string} uploaded_at - Upload-Zeitpunkt (UTC, "YYYY-MM-DD HH:MM:SS")
 * @property {string|null} last_check_started_at - Start der letzten Prüfung (UTC)
 * @property {string|null} last_check_finished_at - Ende der letzten Prüfung (UTC)
 * @property {number} reference_count - Anzahl der Quellen in der Datei
 * @property {{open: number, accepted: number, rejected: number}} finding_counts - Findings je Status
 */

/**
 * Lädt alle gespeicherten Prüfungen, neueste zuerst.
 * @returns {Promise} Axios-Response mit einer Liste von UploadSummary
 */
export const listUploads = () =>
  axios.get(`${BASE_URL}/uploads`)

/**
 * Lädt eine gespeicherte Prüfung mit allen Findings (inkl. Status).
 * @param {number} uploadId - ID der Prüfung
 * @returns {Promise} Axios-Response mit UploadSummary plus findings
 */
export const getUpload = (uploadId) =>
  axios.get(`${BASE_URL}/uploads/${uploadId}`)

/**
 * Löscht eine gespeicherte Prüfung samt Quellen und Findings.
 * @param {number} uploadId - ID der Prüfung
 * @returns {Promise} Axios-Response
 */
export const deleteUpload = (uploadId) =>
  axios.delete(`${BASE_URL}/uploads/${uploadId}`)
