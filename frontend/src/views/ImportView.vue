
<template>
  <div>
    <h1 class="text-2xl font-semibold text-gray-900 mb-2">Literaturdaten importieren</h1>
    <p class="text-gray-500 mb-8">Unterstützte Formate: .bib, .txt, .pdf</p>

    <div
      class="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition"
      @click="triggerFileInput"
      @dragover.prevent
      @drop.prevent="handleDrop"
    >
      <p class="text-gray-400 text-sm mb-3">Datei hier hineinziehen oder</p>
      <button class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition">
        Datei auswählen
      </button>
      <input ref="fileInput" type="file" accept=".bib,.txt,.pdf" class="hidden" @change="handleFileChange" />
    </div>

    <div v-if="selectedFile" class="mt-6 p-4 bg-white border border-gray-200 rounded-lg flex items-center justify-between">
      <span class="text-sm text-gray-700">{{ selectedFile.name }}</span>
      <button
        class="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition disabled:opacity-50"
        :disabled="uploading"
        @click="uploadFile"
      >
        {{ uploading ? 'Wird geprüft…' : 'Prüfung starten' }}
      </button>
    </div>

    <p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup>
/**
 * ImportView — Seite zum Hochladen einer Literaturdatei (.bib, .txt, .pdf).
 * Unterstützt Klick-Auswahl und Drag & Drop.
 * Nach Auswahl wird die Prüfung über uploadFile() gestartet.
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

/** @type {import('vue').Ref<HTMLInputElement|null>} Verstecktes File-Input-Element */
const fileInput = ref(null)

/** @type {import('vue').Ref<File|null>} Aktuell ausgewählte Datei */
const selectedFile = ref(null)

/** Öffnet den nativen Datei-Dialog. */
const triggerFileInput = () => fileInput.value.click()

/**
 * Setzt selectedFile wenn der Nutzer eine Datei über den Dialog auswählt.
 * @param {Event} e - Change-Event des File-Inputs
 */
const handleFileChange = (e) => {
  selectedFile.value = e.target.files[0]
}

/**
 * Setzt selectedFile wenn der Nutzer eine Datei per Drag & Drop ablegt.
 * @param {DragEvent} e - Drop-Event
 */
const handleDrop = (e) => {
  selectedFile.value = e.dataTransfer.files[0]
}

import { importFile, runValidation } from '../services/api.js'

const uploading = ref(false)
const error = ref(null)

/**
 * Sendet die Datei ans Backend, startet die Validierung und navigiert zur Ergebnisseite.
 * Die upload_id aus dem Import wird mitgegeben: So wird genau diese Datei geprüft und
 * die Ergebnisseite kann auf die gespeicherte Prüfung (/uploads/:id) verlinken.
 */
const uploadFile = async () => {
  uploading.value = true
  error.value = null
  try {
    const imported = await importFile(selectedFile.value)
    const uploadId = imported?.data?.upload_id
    const response = await runValidation(uploadId)
    router.push({ path: '/results', state: { results: response.data, uploadId } })
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Fehler beim Upload'
  } finally {
    uploading.value = false
  }
}
</script>
