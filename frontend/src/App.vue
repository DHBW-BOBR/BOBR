<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white border-b border-gray-200">
      <div class="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
        <span class="text-lg font-semibold text-gray-900">BOBR</span>
        <div class="flex gap-6 text-sm">
          <router-link to="/" class="text-gray-600 hover:text-gray-900">Import</router-link>
          <router-link to="/results" class="text-gray-600 hover:text-gray-900">Ergebnisse</router-link>
        </div>
      </div>
    </nav>
    <main class="max-w-5xl mx-auto px-6 py-10">
      <router-view />
    </main>
  </div>
</template>
