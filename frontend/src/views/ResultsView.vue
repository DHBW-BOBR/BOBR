<template>
  <div>
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-semibold text-gray-900">Prüfergebnisse</h1>
      <span class="text-sm text-gray-500">{{ results.length }} Probleme gefunden</span>
    </div>

    <div v-if="results.length === 0" class="text-center py-16 text-gray-400">
      Keine Probleme gefunden.
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="result in results"
        :key="result.id"
        class="bg-white border border-gray-200 rounded-lg p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <span class="text-xs font-medium px-2 py-1 rounded-full mr-2"
              :class="{
                'bg-red-100 text-red-700': result.type === 'fehler',
                'bg-yellow-100 text-yellow-700': result.type === 'warnung',
              }"
            >
              {{ result.type }}
            </span>
            <span class="text-sm font-medium text-gray-900">{{ result.field }}</span>
            <p class="mt-1 text-sm text-gray-600">{{ result.message }}</p>
            <p class="mt-1 text-sm text-blue-600">Vorschlag: {{ result.suggestion }}</p>
          </div>
          <div class="flex gap-2 shrink-0">
            <button
              class="px-3 py-1.5 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition"
              @click="accept(result.id)"
            >
              Annehmen
            </button>
            <button
              class="px-3 py-1.5 text-sm bg-gray-50 text-gray-600 rounded-lg hover:bg-gray-100 transition"
              @click="reject(result.id)"
            >
              Ablehnen
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * ResultsView — Zeigt die Prüfergebnisse nach dem Import.
 * Jedes Problem kann einzeln angenommen oder abgelehnt werden.
 * Ergebnisse werden nach Entscheidung aus der Liste entfernt.
 */
import { ref } from 'vue'

/**
 * @typedef {Object} Result
 * @property {number} id - Eindeutige ID des Problems
 * @property {'fehler'|'warnung'} type - Schweregrad
 * @property {string} field - Betroffenes Feld (z.B. DOI, Autor)
 * @property {string} message - Beschreibung des Problems
 * @property {string} suggestion - Korrekturvorschlag
 */

/** @type {import('vue').Ref<Result[]>} Liste der gefundenen Probleme */
const results = ref([
  { id: 1, type: 'fehler', field: 'DOI', message: 'Ungültiges DOI-Format bei Müller (2023)', suggestion: '10.1000/xyz123' },
  { id: 2, type: 'warnung', field: 'Autor', message: 'Inkonsistente Schreibweise: "Müller, Max" und "Max Müller"', suggestion: 'Müller, Max' },
  { id: 3, type: 'fehler', field: 'Jahr', message: 'Fehlende Jahresangabe bei Schmidt et al.', suggestion: 'Pflichtfeld ergänzen' },
])

/**
 * Nimmt einen Korrekturvorschlag an und entfernt ihn aus der Liste.
 * @param {number} id - ID des Problems
 */
const accept = (id) => {
  results.value = results.value.filter(r => r.id !== id)
}

/**
 * Lehnt einen Korrekturvorschlag ab und entfernt ihn aus der Liste.
 * @param {number} id - ID des Problems
 */
const reject = (id) => {
  results.value = results.value.filter(r => r.id !== id)
}
</script>
