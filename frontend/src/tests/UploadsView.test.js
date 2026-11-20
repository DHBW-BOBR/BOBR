/**
 * Tests für UploadsView.
 * Prüft Anzeige der gespeicherten Prüfungen, Leer- und Fehlerzustand,
 * erneutes Prüfen und Löschen (mit Rückfrage).
 * Die API wird gemockt, der Router läuft als In-Memory-Router.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import UploadsView from '../views/UploadsView.vue'
import { deleteUpload, listUploads, runValidation } from '../services/api.js'

vi.mock('../services/api.js')

/** Zwei gespeicherte Prüfungen, wie sie GET /api/uploads liefert. */
const UPLOADS = [
  {
    id: 2,
    file_name: 'ohne_jahr.bib',
    format: 'bib',
    uploaded_at: '2026-11-20 10:47:21',
    last_check_started_at: '2026-11-20 10:47:21',
    last_check_finished_at: '2026-11-20 10:47:22',
    reference_count: 1,
    finding_counts: { open: 1, accepted: 2, rejected: 3 },
  },
  {
    id: 1,
    file_name: 'literatur.bib',
    format: 'bib',
    uploaded_at: '2026-11-20 10:46:26',
    last_check_started_at: null,
    last_check_finished_at: null,
    reference_count: 4,
    finding_counts: { open: 0, accepted: 0, rejected: 0 },
  },
]

const makeRouter = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/uploads', component: UploadsView },
      { path: '/uploads/:id', component: { template: '<div />' } },
    ],
  })

/** Mountet die Seite und wartet, bis die Liste geladen ist. */
const mountView = async (router = makeRouter()) => {
  await router.push('/uploads')
  const wrapper = mount(UploadsView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('UploadsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    listUploads.mockResolvedValue({ data: structuredClone(UPLOADS) })
  })

  it('zeigt eine Karte je gespeicherter Prüfung', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.findAll('.bg-white.border').length).toBe(2)
    expect(wrapper.text()).toContain('ohne_jahr.bib')
    expect(wrapper.text()).toContain('literatur.bib')
    expect(wrapper.text()).toContain('2 Prüfungen')
  })

  it('zeigt Findings je Status als Badges', async () => {
    const { wrapper } = await mountView()
    const first = wrapper.findAll('.bg-white.border')[0]
    expect(first.find('.status-open').text()).toBe('1 offen')
    expect(first.find('.status-accepted').text()).toBe('2 angenommen')
    expect(first.find('.status-rejected').text()).toBe('3 abgelehnt')
  })

  it('zeigt an, wenn eine Datei noch nicht geprüft wurde', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.findAll('.bg-white.border')[1].text()).toContain('Noch nicht geprüft')
  })

  it('verlinkt Öffnen auf die Detailseite', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.find('a.btn-open').attributes('href')).toBe('/uploads/2')
  })

  it('zeigt einen Hinweis, wenn noch nichts gespeichert ist', async () => {
    listUploads.mockResolvedValue({ data: [] })
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('Noch keine Prüfungen gespeichert')
  })

  it('zeigt eine Fehlermeldung, wenn das Backend nicht erreichbar ist', async () => {
    listUploads.mockRejectedValue(new Error('Network Error'))
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('Läuft das Backend?')
  })

  it('prüft eine Datei erneut und öffnet danach die Detailseite', async () => {
    runValidation.mockResolvedValue({ data: [] })
    const { wrapper, router } = await mountView()
    await wrapper.findAll('button.btn-recheck')[0].trigger('click')
    await flushPromises()
    expect(runValidation).toHaveBeenCalledWith(2)
    expect(router.currentRoute.value.path).toBe('/uploads/2')
  })

  it('löscht eine Prüfung nach Bestätigung', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    deleteUpload.mockResolvedValue({ data: { deleted: 2 } })
    const { wrapper } = await mountView()
    await wrapper.findAll('button.btn-delete')[0].trigger('click')
    await flushPromises()
    expect(deleteUpload).toHaveBeenCalledWith(2)
    expect(wrapper.findAll('.bg-white.border').length).toBe(1)
  })

  it('löscht nichts, wenn die Rückfrage abgebrochen wird', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { wrapper } = await mountView()
    await wrapper.findAll('button.btn-delete')[0].trigger('click')
    await flushPromises()
    expect(deleteUpload).not.toHaveBeenCalled()
    expect(wrapper.findAll('.bg-white.border').length).toBe(2)
  })
})
