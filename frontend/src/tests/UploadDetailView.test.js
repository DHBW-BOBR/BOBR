/**
 * Tests für UploadDetailView.
 * Prüft Filter nach Status, Annehmen/Ablehnen (Finding wechselt den Filter statt zu
 * verschwinden), erneutes Prüfen und die Meldung bei unbekannter Prüfung.
 * Die API wird gemockt, der Router läuft als In-Memory-Router.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import UploadDetailView from '../views/UploadDetailView.vue'
import { acceptCorrection, getUpload, rejectCorrection, runValidation } from '../services/api.js'

vi.mock('../services/api.js')

/** Eine gespeicherte Prüfung, wie sie GET /api/uploads/{id} liefert. */
const UPLOAD = {
  id: 2,
  file_name: 'literatur.bib',
  format: 'bib',
  uploaded_at: '2026-11-20 10:47:21',
  last_check_started_at: '2026-11-20 10:47:21',
  last_check_finished_at: '2026-11-20 10:47:22',
  reference_count: 3,
  finding_counts: { open: 2, accepted: 1, rejected: 0 },
  findings: [
    { id: 10, type: 'fehler', field: 'Vollständigkeit', message: 'Pflichtfelder fehlen bei a1: year', suggestion: 'Fehlende Felder ergänzen', status: 'open', reference_ids: [101] },
    { id: 11, type: 'warnung', field: 'Duplikat', message: 'b1 ähnelt: c1', suggestion: null, status: 'open', reference_ids: [102] },
    { id: 12, type: 'fehler', field: 'DOI', message: 'DOI-Format ungültig bei c1', suggestion: 'Format gemäß Standard korrigieren', status: 'accepted', reference_ids: [102] },
  ],
  references: [
    { id: 101, position: 1, citekey: 'a1', type: 'article', title: 'Erster Artikel', authors: ['Smith, John'], year: null, container: 'Journal', publisher: null, doi: null, isbn: null, url: null, raw_text: null },
    { id: 102, position: 2, citekey: 'b1', type: 'book', title: 'Zweites Buch', authors: ['Doe, Jane', 'Roe, Rick'], year: 2020, container: null, publisher: 'Verlag', doi: '10.1/x', isbn: null, url: null, raw_text: null },
    { id: 103, position: 3, citekey: null, type: null, title: null, authors: [], year: 2026, container: null, publisher: null, doi: null, isbn: null, url: null, raw_text: '-07-09.' },
  ],
}

/** Mountet die Detailseite für Prüfung `id` und wartet, bis sie geladen ist. */
const mountView = async (id = 2) => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/uploads', component: { template: '<div />' } },
      { path: '/uploads/:id', component: UploadDetailView },
    ],
  })
  await router.push(`/uploads/${id}`)
  const wrapper = mount(UploadDetailView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

/** Klickt den Filter-Knopf, dessen Text mit `label` beginnt. */
const clickTab = async (wrapper, label) => {
  const tab = wrapper.findAll('button.filter-tab').find(b => b.text().startsWith(label))
  await tab.trigger('click')
}

describe('UploadDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getUpload.mockResolvedValue({ data: structuredClone(UPLOAD) })
  })

  it('lädt die Prüfung über die ID aus der Adresse', async () => {
    const wrapper = await mountView()
    expect(getUpload).toHaveBeenCalledWith('2')
    expect(wrapper.text()).toContain('literatur.bib')
  })

  it('zeigt zuerst nur offene Findings', async () => {
    const wrapper = await mountView()
    expect(wrapper.findAll('.finding').length).toBe(2)
    expect(wrapper.text()).toContain('Offen (2)')
    expect(wrapper.text()).toContain('Angenommen (1)')
  })

  it('zeigt entschiedene Findings im passenden Filter mit Status', async () => {
    const wrapper = await mountView()
    await clickTab(wrapper, 'Angenommen')
    const cards = wrapper.findAll('.finding')
    expect(cards.length).toBe(1)
    expect(cards[0].text()).toContain('DOI-Format ungültig')
    expect(cards[0].text()).toContain('angenommen')
    expect(cards[0].find('button').exists()).toBe(false)
  })

  it('zeigt unter Alle sämtliche Findings', async () => {
    const wrapper = await mountView()
    await clickTab(wrapper, 'Alle')
    expect(wrapper.findAll('.finding').length).toBe(3)
  })

  it('verschiebt ein angenommenes Finding in den Filter Angenommen', async () => {
    acceptCorrection.mockResolvedValue({ data: { status: 'accepted', id: 10 } })
    const wrapper = await mountView()
    await wrapper.findAll('button.bg-green-50')[0].trigger('click')
    await flushPromises()
    expect(acceptCorrection).toHaveBeenCalledWith(10)
    expect(wrapper.findAll('.finding').length).toBe(1)
    expect(wrapper.text()).toContain('Angenommen (2)')
  })

  it('verschiebt ein abgelehntes Finding in den Filter Abgelehnt', async () => {
    rejectCorrection.mockResolvedValue({ data: { status: 'rejected', id: 10 } })
    const wrapper = await mountView()
    await wrapper.findAll('button.bg-gray-50')[0].trigger('click')
    await flushPromises()
    expect(rejectCorrection).toHaveBeenCalledWith(10)
    await clickTab(wrapper, 'Abgelehnt')
    expect(wrapper.findAll('.finding').length).toBe(1)
    expect(wrapper.text()).toContain('abgelehnt')
  })

  it('prüft erneut und lädt die Findings neu', async () => {
    runValidation.mockResolvedValue({ data: [] })
    const wrapper = await mountView()
    await wrapper.find('button.btn-recheck').trigger('click')
    await flushPromises()
    expect(runValidation).toHaveBeenCalledWith(2)
    expect(getUpload).toHaveBeenCalledTimes(2)
  })

  it('meldet eine unbekannte Prüfung', async () => {
    getUpload.mockRejectedValue({ response: { status: 404, data: { detail: 'nicht gefunden' } } })
    const wrapper = await mountView(99)
    expect(wrapper.text()).toContain('Diese Prüfung gibt es nicht (mehr).')
  })
})

describe('UploadDetailView – Reiter Quellen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getUpload.mockResolvedValue({ data: structuredClone(UPLOAD) })
  })

  it('zeigt die Anzahl der erkannten Quellen im Reiter', async () => {
    const wrapper = await mountView()
    expect(wrapper.text()).toContain('Quellen (3)')
  })

  it('zeigt jede erkannte Quelle mit ihren Angaben', async () => {
    const wrapper = await mountView()
    await clickTab(wrapper, 'Quellen')
    const cards = wrapper.findAll('.source')
    expect(cards.length).toBe(3)
    expect(cards[1].text()).toContain('#2')
    expect(cards[1].text()).toContain('Zweites Buch')
    expect(cards[1].text()).toContain('Doe, Jane; Roe, Rick · 2020 · Verlag')
    expect(cards[1].text()).toContain('DOI 10.1/x')
  })

  it('ordnet die Findings den Quellen zu', async () => {
    const wrapper = await mountView()
    await clickTab(wrapper, 'Quellen')
    const cards = wrapper.findAll('.source')
    expect(cards[0].text()).toContain('Pflichtfelder fehlen bei a1')
    expect(cards[0].find('.source-status').text()).toBe('1 offen')
    expect(cards[1].text()).toContain('b1 ähnelt: c1')
    expect(cards[1].text()).toContain('(angenommen)')
  })

  it('markiert Quellen ohne Findings als in Ordnung', async () => {
    const wrapper = await mountView()
    await clickTab(wrapper, 'Quellen')
    expect(wrapper.findAll('.source')[2].find('.source-status').text()).toBe('in Ordnung')
  })

  it('zeigt bei .txt/.pdf den erkannten Originaltext und fehlende Angaben', async () => {
    const wrapper = await mountView()
    await clickTab(wrapper, 'Quellen')
    const card = wrapper.findAll('.source')[2]
    expect(card.find('.raw-text').text()).toBe('Erkannt aus: -07-09.')
    expect(card.text()).toContain('Kein Titel erkannt')
  })

  it('zeigt alles entschieden, wenn keine offenen Findings mehr da sind', async () => {
    acceptCorrection.mockResolvedValue({ data: {} })
    const wrapper = await mountView()
    await wrapper.findAll('button.bg-green-50')[1].trigger('click')
    await flushPromises()
    await clickTab(wrapper, 'Quellen')
    expect(wrapper.findAll('.source')[1].find('.source-status').text()).toBe('alles entschieden')
  })
})
