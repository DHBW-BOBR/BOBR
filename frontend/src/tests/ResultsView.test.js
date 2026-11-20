/**
 * Tests für ResultsView.
 * Prüft Anzeige der Probleme, Annehmen/Ablehnen von Korrekturen,
 * die Leer-Meldung wenn alle Einträge bearbeitet wurden und den Link zur gespeicherten Prüfung.
 * Die Ergebnisse kommen wie im echten Ablauf über history.state (von ImportView gesetzt),
 * die API wird gemockt.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import ResultsView from '../views/ResultsView.vue'
import { acceptCorrection, rejectCorrection } from '../services/api.js'

vi.mock('../services/api.js')

/** Drei Findings, wie sie POST /api/validate/ liefert. */
const RESULTS = [
  { id: 1, type: 'fehler', field: 'Vollständigkeit', message: 'Jahr fehlt', suggestion: 'Jahr ergänzen' },
  { id: 2, type: 'warnung', field: 'DOI', message: 'DOI ungültig', suggestion: 'DOI prüfen' },
  { id: 3, type: 'fehler', field: 'ISBN', message: 'Prüfziffer falsch', suggestion: 'ISBN prüfen' },
]

/** Setzt history.state wie nach router.push aus ImportView und rendert die Seite. */
const mountWithState = (state = { results: RESULTS }) => {
  history.replaceState(state, '')
  return mount(ResultsView, { global: { stubs: { RouterLink: RouterLinkStub } } })
}

describe('ResultsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    acceptCorrection.mockResolvedValue({ data: { status: 'accepted' } })
    rejectCorrection.mockResolvedValue({ data: { status: 'rejected' } })
  })

  it('zeigt alle Probleme an', () => {
    const wrapper = mountWithState()
    expect(wrapper.findAll('.bg-white.border').length).toBe(3)
  })

  it('zeigt die Anzahl der Probleme an', () => {
    const wrapper = mountWithState()
    expect(wrapper.text()).toContain('3 Probleme gefunden')
  })

  it('entfernt Eintrag nach Klick auf Annehmen', async () => {
    const wrapper = mountWithState()
    await wrapper.findAll('button.bg-green-50')[0].trigger('click')
    await flushPromises()
    expect(acceptCorrection).toHaveBeenCalledWith(1)
    expect(wrapper.findAll('.bg-white.border').length).toBe(2)
  })

  it('entfernt Eintrag nach Klick auf Ablehnen', async () => {
    const wrapper = mountWithState()
    await wrapper.findAll('button.bg-gray-50')[0].trigger('click')
    await flushPromises()
    expect(rejectCorrection).toHaveBeenCalledWith(1)
    expect(wrapper.findAll('.bg-white.border').length).toBe(2)
  })

  it('zeigt Meldung wenn keine Probleme vorhanden', async () => {
    const wrapper = mountWithState()
    for (const btn of wrapper.findAll('button.bg-green-50')) {
      await btn.trigger('click')
      await flushPromises()
    }
    expect(wrapper.text()).toContain('Keine Probleme gefunden')
  })

  it('zeigt Keine Probleme, wenn die Seite ohne Ergebnisse geöffnet wird', () => {
    const wrapper = mountWithState(null)
    expect(wrapper.text()).toContain('0 Probleme gefunden')
    expect(wrapper.text()).toContain('Keine Probleme gefunden')
  })

  it('verlinkt auf die gespeicherte Prüfung, wenn eine upload_id mitkommt', () => {
    const wrapper = mountWithState({ results: RESULTS, uploadId: 7 })
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/uploads/7')
  })

  it('zeigt keinen Link ohne upload_id', () => {
    const wrapper = mountWithState()
    expect(wrapper.findComponent(RouterLinkStub).exists()).toBe(false)
  })
})
