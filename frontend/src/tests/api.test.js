/**
 * Tests für api.js.
 * Axios wird gemockt — es werden keine echten HTTP-Anfragen gestellt.
 * Prüft ob alle Funktionen die richtigen Endpunkte und Parameter verwenden.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'
import { importFile, runValidation, acceptCorrection, rejectCorrection } from '../services/api'

vi.mock('axios')

describe('api.js', () => {
  beforeEach(() => vi.clearAllMocks())

  it('importFile sendet Datei als multipart/form-data', async () => {
    axios.post.mockResolvedValue({ data: {} })
    const file = new File(['inhalt'], 'literatur.bib')
    await importFile(file)
    const formData = axios.post.mock.calls[0][1]
    expect(axios.post).toHaveBeenCalledWith(
      'http://localhost:8000/api/import/',
      expect.any(FormData)
    )
    expect(formData.get('file')).toBe(file)
  })

  it('runValidation ruft POST /api/validate/ auf', async () => {
    axios.post.mockResolvedValue({ data: [] })
    await runValidation()
    expect(axios.post).toHaveBeenCalledWith('http://localhost:8000/api/validate/')
  })

  it('acceptCorrection ruft POST /api/corrections/{id}/accept auf', async () => {
    axios.post.mockResolvedValue({ data: {} })
    await acceptCorrection(1)
    expect(axios.post).toHaveBeenCalledWith('http://localhost:8000/api/corrections/1/accept')
  })

  it('rejectCorrection ruft POST /api/corrections/{id}/reject auf', async () => {
    axios.post.mockResolvedValue({ data: {} })
    await rejectCorrection(2)
    expect(axios.post).toHaveBeenCalledWith('http://localhost:8000/api/corrections/2/reject')
  })
})
