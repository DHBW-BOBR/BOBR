<template>
  <div>
    <router-link to="/uploads" class="text-sm text-gray-500 hover:text-gray-900">← Alle Prüfungen</router-link>

    <p v-if="error" class="mt-6 text-sm text-red-600">{{ error }}</p>

    <div v-if="loading" class="text-center py-16 text-gray-400">
      Prüfung wird geladen…
    </div>

    <template v-else-if="upload">
      <div class="flex items-start justify-between gap-4 mt-4 mb-2">
        <h1 class="text-2xl font-semibold text-gray-900">{{ upload.file_name }}</h1>
        <button
          class="btn-recheck px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition disabled:opacity-50 shrink-0"
          :disabled="checking"
          @click="recheck"
        >
          {{ checking ? 'Wird geprüft…' : 'Erneut prüfen' }}
        </button>
      </div>
      <p class="text-gray-500 mb-8">
        Hochgeladen am {{ formatDate(upload.uploaded_at) }} · {{ upload.reference_count }}
        {{ upload.reference_count === 1 ? 'Quelle' : 'Quellen' }} · {{ checkStatusText(upload) }}
      </p>

      <div class="flex flex-wrap gap-2 mb-6">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="filter-tab px-3 py-1.5 text-sm rounded-lg transition"
          :class="filter === tab.value
            ? 'bg-blue-600 text-white'
            : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'"
          @click="filter = tab.value"
        >
          {{ tab.label }} ({{ counts[tab.value] }})
        </button>
      </div>

      <div v-if="visibleFindings.length === 0" class="text-center py-16 text-gray-400">
        {{ emptyText }}
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="finding in visibleFindings"
          :key="finding.id"
          class="finding bg-white border border-gray-200 rounded-lg p-5"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <span class="text-xs font-medium px-2 py-1 rounded-full mr-2"
                :class="{
                  'bg-red-100 text-red-700': finding.type === 'fehler',
                  'bg-yellow-100 text-yellow-700': finding.type === 'warnung',
                }"
              >
                {{ finding.type }}
              </span>
              <span class="text-sm font-medium text-gray-900">{{ finding.field }}</span>
              <p class="mt-1 text-sm text-gray-600">{{ finding.message }}</p>
              <p v-if="finding.suggestion" class="mt-1 text-sm text-blue-600">Vorschlag: {{ finding.suggestion }}</p>
            </div>
            <div v-if="finding.status === 'open'" class="flex gap-2 shrink-0">
              <button
                class="px-3 py-1.5 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition"
                @click="decide(finding, 'accepted')"
              >
                Annehmen
              </button>
              <button
                class="px-3 py-1.5 text-sm bg-gray-50 text-gray-600 rounded-lg hover:bg-gray-100 transition"
                @click="decide(finding, 'rejected')"
              >
                Ablehnen
              </button>
            </div>
            <span
              v-else
              class="text-xs font-medium px-2 py-1 rounded-full shrink-0"
              :class="finding.status === 'accepted' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'"
            >
              {{ finding.status === 'accepted' ? 'angenommen' : 'abgelehnt' }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
/**
 * UploadDetailView — Eine gespeicherte Prüfung mit allen Findings und ihrem Status.
 * Offene Findings können angenommen oder abgelehnt werden; bereits entschiedene
 * bleiben sichtbar und lassen sich über die Filter wiederfinden.
 *
 * Warum: Der Nutzer soll nachvollziehen können, was er bei einer Datei schon entschieden hat,
 * und auch nach einem Neustart weiterarbeiten können.
 * Alternativen: ResultsView erweitern; verworfen, weil ResultsView die Ergebnisse direkt
 * nach dem Import zeigt (entschiedene verschwinden dort) und Mariekes Ablauf so unverändert bleibt.
 * Entschiedene Findings werden hier nicht entfernt, sondern wandern in den passenden Filter.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { acceptCorrection, getUpload, rejectCorrection, runValidation } from '../services/api.js'
import { checkStatusText, formatDate } from '../utils/format.js'

const route = useRoute()

/**
 * @typedef {Object} Finding
 * @property {number} id - Eindeutige ID des Problems
 * @property {'fehler'|'warnung'} type - Schweregrad
 * @property {string} field - Betroffenes Feld (z.B. DOI, Autor)
 * @property {string} message - Beschreibung des Problems
 * @property {string|null} suggestion - Korrekturvorschlag
 * @property {'open'|'accepted'|'rejected'} status - Entscheidung des Nutzers
 */

/** Filter oberhalb der Liste; "open" ist voreingestellt, weil dort noch Arbeit wartet. */
const tabs = [
  { value: 'open', label: 'Offen' },
  { value: 'accepted', label: 'Angenommen' },
  { value: 'rejected', label: 'Abgelehnt' },
  { value: 'all', label: 'Alle' },
]

/** @type {import('vue').Ref<Object|null>} Metadaten der Prüfung inkl. findings */
const upload = ref(null)

/** @type {import('vue').Ref<Finding[]>} Alle Findings dieser Prüfung */
const findings = ref([])

/** @type {import('vue').Ref<'open'|'accepted'|'rejected'|'all'>} Aktiver Filter */
const filter = ref('open')

const loading = ref(true)
const checking = ref(false)
const error = ref(null)

/** Anzahl der Findings je Filter (für die Beschriftung der Filter-Knöpfe). */
const counts = computed(() => ({
  open: findings.value.filter(f => f.status === 'open').length,
  accepted: findings.value.filter(f => f.status === 'accepted').length,
  rejected: findings.value.filter(f => f.status === 'rejected').length,
  all: findings.value.length,
}))

/** Findings, die zum aktiven Filter passen. */
const visibleFindings = computed(() =>
  filter.value === 'all' ? findings.value : findings.value.filter(f => f.status === filter.value)
)

/** Hinweis, wenn im aktiven Filter nichts steht. */
const emptyText = computed(() => ({
  open: 'Keine offenen Probleme.',
  accepted: 'Noch nichts angenommen.',
  rejected: 'Noch nichts abgelehnt.',
  all: 'Keine Probleme gefunden.',
}[filter.value]))

/** Lädt die Prüfung mit allen Findings vom Backend. */
const load = async () => {
  error.value = null
  try {
    const response = await getUpload(route.params.id)
    upload.value = response.data
    findings.value = response.data.findings
  } catch (e) {
    upload.value = null
    error.value = e.response?.status === 404
      ? 'Diese Prüfung gibt es nicht (mehr).'
      : (e.response?.data?.detail ?? 'Prüfung konnte nicht geladen werden. Läuft das Backend?')
  } finally {
    loading.value = false
  }
}

/**
 * Prüft die Datei erneut und lädt danach die Findings neu.
 * Offene Findings werden dabei neu erzeugt, entschiedene bleiben erhalten.
 */
const recheck = async () => {
  checking.value = true
  error.value = null
  try {
    await runValidation(upload.value.id)
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Fehler bei der Prüfung'
  } finally {
    checking.value = false
  }
}

/**
 * Nimmt ein Finding an oder lehnt es ab und aktualisiert seinen Status in der Liste.
 * @param {Finding} finding - Das betroffene Finding
 * @param {'accepted'|'rejected'} status - Neue Entscheidung
 */
const decide = async (finding, status) => {
  error.value = null
  try {
    await (status === 'accepted' ? acceptCorrection(finding.id) : rejectCorrection(finding.id))
    finding.status = status
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Entscheidung konnte nicht gespeichert werden'
  }
}

onMounted(load)
</script>
