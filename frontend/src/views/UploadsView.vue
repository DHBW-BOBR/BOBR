<template>
  <div>
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-2xl font-semibold text-gray-900">Gespeicherte Prüfungen</h1>
      <span class="text-sm text-gray-500">{{ uploads.length }} Prüfungen</span>
    </div>

    <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>

    <div v-if="loading" class="text-center py-16 text-gray-400">
      Prüfungen werden geladen…
    </div>

    <div v-else-if="uploads.length === 0" class="text-center py-16 text-gray-400">
      Noch keine Prüfungen gespeichert.
      <router-link to="/" class="text-blue-600 hover:text-blue-700">Datei importieren</router-link>
    </div>

    <div v-else class="space-y-4">
      <div
        v-for="upload in uploads"
        :key="upload.id"
        class="bg-white border border-gray-200 rounded-lg p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <span class="text-xs font-medium px-2 py-1 rounded-full mr-2 bg-gray-100 text-gray-600 uppercase">
              {{ upload.format }}
            </span>
            <span class="text-sm font-medium text-gray-900">{{ upload.file_name }}</span>
            <p class="mt-1 text-sm text-gray-600">
              Hochgeladen am {{ formatDate(upload.uploaded_at) }} · {{ upload.reference_count }}
              {{ upload.reference_count === 1 ? 'Quelle' : 'Quellen' }}
            </p>
            <p class="mt-1 text-sm text-gray-500">{{ checkStatusText(upload) }}</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <span class="status-open text-xs font-medium px-2 py-1 rounded-full bg-blue-100 text-blue-700">
                {{ upload.finding_counts.open }} offen
              </span>
              <span class="status-accepted text-xs font-medium px-2 py-1 rounded-full bg-green-100 text-green-700">
                {{ upload.finding_counts.accepted }} angenommen
              </span>
              <span class="status-rejected text-xs font-medium px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                {{ upload.finding_counts.rejected }} abgelehnt
              </span>
            </div>
          </div>
          <div class="flex gap-2 shrink-0">
            <router-link
              :to="`/uploads/${upload.id}`"
              class="btn-open px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition"
            >
              Öffnen
            </router-link>
            <button
              class="btn-recheck px-3 py-1.5 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition disabled:opacity-50"
              :disabled="busyId === upload.id"
              @click="recheck(upload)"
            >
              {{ busyId === upload.id ? 'Wird geprüft…' : 'Erneut prüfen' }}
            </button>
            <button
              class="btn-delete px-3 py-1.5 text-sm bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition disabled:opacity-50"
              :disabled="busyId === upload.id"
              @click="remove(upload)"
            >
              Löschen
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * UploadsView — Übersicht aller gespeicherten Prüfungen (eine Karte je hochgeladener Datei).
 * Von hier aus kann der Nutzer eine Prüfung öffnen, erneut prüfen oder löschen.
 *
 * Warum: Das Backend speichert jeden Upload dauerhaft. Ohne diese Seite käme der Nutzer
 * nach einem Neuladen oder Neustart nicht mehr an seine Prüfungen und Entscheidungen.
 * Alternativen: Liste direkt auf der Import-Seite unter dem Upload-Feld; verworfen, weil
 * die Import-Seite dann überladen wäre und die Übersicht eine eigene Adresse (/uploads)
 * zum Verlinken bekommen soll.
 */
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteUpload, listUploads, runValidation } from '../services/api.js'
import { checkStatusText, formatDate } from '../utils/format.js'

const router = useRouter()

/** @type {import('vue').Ref<import('../services/api.js').UploadSummary[]>} Gespeicherte Prüfungen */
const uploads = ref([])

/** @type {import('vue').Ref<boolean>} true solange die Liste geladen wird */
const loading = ref(true)

/** @type {import('vue').Ref<string|null>} Fehlermeldung für den Nutzer */
const error = ref(null)

/** @type {import('vue').Ref<number|null>} ID der Prüfung, die gerade bearbeitet wird (sperrt ihre Knöpfe) */
const busyId = ref(null)

/** Lädt die Liste der gespeicherten Prüfungen vom Backend. */
const load = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await listUploads()
    uploads.value = response.data
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Prüfungen konnten nicht geladen werden. Läuft das Backend?'
  } finally {
    loading.value = false
  }
}

/**
 * Prüft eine gespeicherte Datei erneut und öffnet danach ihre Detailseite.
 * Bereits angenommene oder abgelehnte Findings bleiben dabei erhalten.
 * @param {import('../services/api.js').UploadSummary} upload - Die zu prüfende Prüfung
 */
const recheck = async (upload) => {
  busyId.value = upload.id
  error.value = null
  try {
    await runValidation(upload.id)
    router.push(`/uploads/${upload.id}`)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Fehler bei der Prüfung'
  } finally {
    busyId.value = null
  }
}

/**
 * Löscht eine Prüfung nach Rückfrage und entfernt sie aus der Liste.
 * Warum Rückfrage: Löschen entfernt auch alle Entscheidungen und kann nicht rückgängig gemacht werden.
 * @param {import('../services/api.js').UploadSummary} upload - Die zu löschende Prüfung
 */
const remove = async (upload) => {
  const ok = window.confirm(
    `„${upload.file_name}“ und alle Findings dieser Prüfung löschen? Das kann nicht rückgängig gemacht werden.`
  )
  if (!ok) return
  busyId.value = upload.id
  error.value = null
  try {
    await deleteUpload(upload.id)
    uploads.value = uploads.value.filter(u => u.id !== upload.id)
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Fehler beim Löschen'
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>
