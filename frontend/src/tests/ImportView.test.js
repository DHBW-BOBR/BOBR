/**
 * Tests für ImportView.
 * Prüft Dateiauswahl, Anzeige des Dateinamens und Navigation zur Ergebnisseite.
 * Router wird als In-Memory-Router gemockt.
 */
import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import ImportView from '../views/ImportView.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: ImportView },
    { path: '/results', component: { template: '<div />' } },
  ],
})

describe('ImportView', () => {
  it('zeigt keinen Upload-Button wenn keine Datei ausgewählt ist', () => {
    const wrapper = mount(ImportView, { global: { plugins: [router] } })
    expect(wrapper.find('button.bg-green-600').exists()).toBe(false)
  })

  it('zeigt den Dateinamen nach Dateiauswahl an', async () => {
    const wrapper = mount(ImportView, { global: { plugins: [router] } })
    const file = new File(['inhalt'], 'literatur.bib', { type: 'application/octet-stream' })
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    expect(wrapper.text()).toContain('literatur.bib')
  })

  it('zeigt Upload-Button nach Dateiauswahl an', async () => {
    const wrapper = mount(ImportView, { global: { plugins: [router] } })
    const file = new File(['inhalt'], 'literatur.bib', { type: 'application/octet-stream' })
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    expect(wrapper.find('button.bg-green-600').exists()).toBe(true)
  })

  it('navigiert zu /results nach Klick auf Prüfung starten', async () => {
    const wrapper = mount(ImportView, { global: { plugins: [router] } })
    const file = new File(['inhalt'], 'literatur.bib', { type: 'application/octet-stream' })
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file] })
    await input.trigger('change')
    await wrapper.find('button.bg-green-600').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/results')
  })
})
