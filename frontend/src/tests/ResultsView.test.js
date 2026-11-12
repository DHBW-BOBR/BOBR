/**
 * Tests für ResultsView.
 * Prüft Anzeige der Probleme, Annehmen/Ablehnen von Korrekturen
 * und die Leer-Meldung wenn alle Einträge bearbeitet wurden.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ResultsView from '../views/ResultsView.vue'

describe('ResultsView', () => {
  it('zeigt alle Probleme an', () => {
    const wrapper = mount(ResultsView)
    expect(wrapper.findAll('.bg-white.border').length).toBe(3)
  })

  it('zeigt die Anzahl der Probleme an', () => {
    const wrapper = mount(ResultsView)
    expect(wrapper.text()).toContain('3 Probleme gefunden')
  })

  it('entfernt Eintrag nach Klick auf Annehmen', async () => {
    const wrapper = mount(ResultsView)
    await wrapper.findAll('button.bg-green-50')[0].trigger('click')
    expect(wrapper.findAll('.bg-white.border').length).toBe(2)
  })

  it('entfernt Eintrag nach Klick auf Ablehnen', async () => {
    const wrapper = mount(ResultsView)
    await wrapper.findAll('button.bg-gray-50')[0].trigger('click')
    expect(wrapper.findAll('.bg-white.border').length).toBe(2)
  })

  it('zeigt Meldung wenn keine Probleme vorhanden', async () => {
    const wrapper = mount(ResultsView)
    const acceptButtons = wrapper.findAll('button.bg-green-50')
    for (const btn of acceptButtons) {
      await btn.trigger('click')
    }
    expect(wrapper.text()).toContain('Keine Probleme gefunden')
  })
})
