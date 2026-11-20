/**
 * Tests für ImportView.
 * Prüft Dateiauswahl, Anzeige des Dateinamens, den Ablauf Import -> Prüfung -> Ergebnisseite
 * und die Fehlermeldung bei einem fehlgeschlagenen Upload.
 * Die API wird gemockt (kein Backend nötig), der Router läuft als In-Memory-Router.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ImportView from '../views/ImportView.vue'
import { importFile, runValidation } from '../services/api.js'

vi.mock('../services/api.js')

/** Zwei Findings, wie sie POST /api/validate/ liefert. */
const FINDINGS = [
  { id: 1, type: 'fehler', field: 'Vollständigkeit', message: 'Jahr fehlt', suggestion: 'Jahr ergänzen' },
  { id: 2, type: 'warnung', field: 'DOI', message: 'DOI ungültig', suggestion: 'DOI prüfen' },
]

/** Pro Test ein frischer Router, damit die Navigation eines Tests den nächsten nicht beeinflusst. */
const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: ImportView },
      { path: '/results', component: { template: '<div />' } },
    ],
  })

/** Rendert die Seite und wählt eine Datei über das versteckte File-Input aus. */
const mountWithFile = async (router) => {
  await router.push('/')
  const wrapper = mount(ImportView, { global: { plugins: [router] } })
  const file = new File(['inhalt'], 'literatur.bib', { type: 'application/octet-stream' })
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file] })
  await input.trigger('change')
  return { wrapper, file }
}

describe('ImportView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    importFile.mockResolvedValue({ data: { count: 2, filename: 'literatur.bib', upload_id: 7 } })
    runValidation.mockResolvedValue({ data: FINDINGS })
  })

  it('zeigt keinen Upload-Button wenn keine Datei ausgewählt ist', () => {
    const wrapper = mount(ImportView, { global: { plugins: [makeRouter()] } })
    expect(wrapper.find('button.bg-green-600').exists()).toBe(false)
  })

  it('zeigt den Dateinamen nach Dateiauswahl an', async () => {
    const { wrapper } = await mountWithFile(makeRouter())
    expect(wrapper.text()).toContain('literatur.bib')
  })

  it('zeigt Upload-Button nach Dateiauswahl an', async () => {
    const { wrapper } = await mountWithFile(makeRouter())
    expect(wrapper.find('button.bg-green-600').exists()).toBe(true)
  })

  it('navigiert zu /results nach Klick auf Prüfung starten', async () => {
    const router = makeRouter()
    const { wrapper } = await mountWithFile(router)
    await wrapper.find('button.bg-green-600').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/results')
  })

  it('prüft genau die gerade hochgeladene Datei', async () => {
    const { wrapper, file } = await mountWithFile(makeRouter())
    await wrapper.find('button.bg-green-600').trigger('click')
    await flushPromises()
    expect(importFile).toHaveBeenCalledWith(file)
    // upload_id aus der Import-Antwort wird an die Prüfung weitergegeben
    expect(runValidation).toHaveBeenCalledWith(7)
  })

  it('zeigt die Fehlermeldung des Backends und bleibt auf der Seite', async () => {
    importFile.mockRejectedValue({ response: { data: { detail: 'Datei konnte nicht gelesen werden' } } })
    const router = makeRouter()
    const { wrapper } = await mountWithFile(router)
    await wrapper.find('button.bg-green-600').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Datei konnte nicht gelesen werden')
    expect(router.currentRoute.value.path).toBe('/')
    expect(runValidation).not.toHaveBeenCalled()
  })
})
