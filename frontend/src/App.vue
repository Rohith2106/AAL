<template>
  <div class="min-h-screen bg-gray-50 text-gray-900">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
              <span class="text-white font-bold text-xl">A</span>
            </div>
            <div>
              <h1 class="text-2xl font-bold text-gray-900">Accounting Automation</h1>
              <p class="text-sm text-gray-500">LLM-Powered Receipt Processing</p>
            </div>
          </div>
          <nav class="flex space-x-4">
            <button
              @click="activeTab = 'upload'"
              :class="[
                'px-4 py-2 rounded-lg font-medium transition-colors',
                activeTab === 'upload'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              ]"
            >
              Upload
            </button>
            <button
              @click="activeTab = 'ledger'"
              :class="[
                'px-4 py-2 rounded-lg font-medium transition-colors',
                activeTab === 'ledger'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              ]"
            >
              Ledger
            </button>
            <button
              @click="activeTab = 'chat'"
              :class="[
                'px-4 py-2 rounded-lg font-medium transition-colors',
                activeTab === 'chat'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              ]"
            >
              Chat
            </button>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Upload Tab -->
      <div v-if="activeTab === 'upload'" class="space-y-6">
        <UploadReceipt @receipt-processed="handleReceiptProcessed" />
      </div>

      <!-- Ledger Tab -->
      <div v-if="activeTab === 'ledger'" class="space-y-6">
        <LedgerView />
      </div>

      <!-- Chat Tab -->
      <div v-if="activeTab === 'chat'" class="space-y-6">
        <ChatInterface />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UploadReceipt from './components/UploadReceipt.vue'
import LedgerView from './components/LedgerView.vue'
import ChatInterface from './components/ChatInterface.vue'

const activeTab = ref('upload')

const handleReceiptProcessed = (data) => {
  // Switch to ledger tab after processing
  activeTab.value = 'ledger'
}
</script>
