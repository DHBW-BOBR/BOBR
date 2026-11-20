/**
 * Tests für utils/format.js (Datumsanzeige und Status der letzten Prüfung).
 */
import { describe, it, expect } from 'vitest'
import { checkStatusText, formatDate } from '../utils/format.js'

describe('formatDate', () => {
  it('zeigt einen Strich, wenn kein Zeitpunkt vorhanden ist', () => {
    expect(formatDate(null)).toBe('–')
  })

  it('wandelt UTC-Zeitstempel in ein deutsches Datum um', () => {
    expect(formatDate('2026-11-20 10:47:21')).toContain('20.11.26')
  })
})

describe('checkStatusText', () => {
  it('meldet noch nicht geprüfte Dateien', () => {
    expect(checkStatusText({ last_check_started_at: null, last_check_finished_at: null }))
      .toBe('Noch nicht geprüft')
  })

  it('meldet abgebrochene Prüfungen', () => {
    expect(checkStatusText({ last_check_started_at: '2026-11-20 10:00:00', last_check_finished_at: null }))
      .toBe('Letzte Prüfung wurde abgebrochen')
  })

  it('nennt den Zeitpunkt der letzten abgeschlossenen Prüfung', () => {
    expect(checkStatusText({
      last_check_started_at: '2026-11-20 10:00:00',
      last_check_finished_at: '2026-11-20 10:00:05',
    })).toContain('Zuletzt geprüft am 20.11.26')
  })
})
