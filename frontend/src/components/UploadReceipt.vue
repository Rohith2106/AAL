<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <h2 class="text-2xl font-bold text-gray-900 mb-6">Upload Receipt/Invoice</h2>
    
    <!-- Upload Area -->
    <div
      @drop.prevent="handleDrop"
      @dragover.prevent
      @dragenter.prevent
      :class="[
        'border-2 border-dashed rounded-xl p-12 text-center transition-colors',
        isDragging ? 'border-primary-500 bg-primary-50' : 'border-gray-300 bg-gray-50'
      ]"
    >
      <input
        ref="fileInput"
        type="file"
        accept="image/*,.pdf"
        multiple
        @change="handleFileSelect"
        class="hidden"
      />
      
      <div v-if="!processing && !batchResults">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p class="text-lg font-medium text-gray-700 mb-2">
          Drag and drop your receipts or invoices here
        </p>
        <p class="text-sm text-gray-500 mb-4">or</p>
        <button @click="$refs.fileInput.click()" class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800">
          Browse Files
        </button>
        <p class="text-xs text-gray-400 mt-4">Supports: JPG, PNG, PDF (Multiple files allowed)</p>
      </div>
      
      <!-- Processing -->
      <div v-if="processing" class="space-y-4">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        <p class="text-lg font-medium text-gray-700">{{ processingMessage }}</p>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div class="bg-primary-600 h-2 rounded-full transition-all duration-300" :style="{ width: progress + '%' }"></div>
        </div>
        <p v-if="processingFileCount > 0" class="text-sm text-gray-500">
          Processing {{ currentFileIndex }} of {{ processingFileCount }} files...
        </p>
      </div>
    </div>

    <!-- OCR Engine Selection -->
    <div v-if="!processing && !batchResults" class="mt-6">
      <label class="block text-sm font-medium text-gray-700 mb-2">OCR Engine</label>
      <select v-model="ocrEngine" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all">
        <option value="easyocr">EasyOCR (Recommended)</option>
        <option value="tesseract">Tesseract OCR</option>
      </select>
    </div>

    <!-- Batch Results -->
    <div v-if="batchResults" class="mt-6 space-y-6">
      <div class="border-t pt-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-gray-900">Batch Processing Results</h3>
          <div class="flex items-center space-x-4">
            <span class="text-sm text-green-600 font-medium">✓ {{ batchResults.successful }} successful</span>
            <span v-if="batchResults.failed > 0" class="text-sm text-red-600 font-medium">✗ {{ batchResults.failed }} failed</span>
          </div>
        </div>

        <!-- Results List -->
        <div class="space-y-4">
          <div
            v-for="(result, index) in batchResults.results"
            :key="result.record_id"
            class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center space-x-3 mb-2">
                  <span
                    :class="[
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      result.status === 'validated'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    ]"
                  >
                    {{ result.status === 'validated' ? '✓ Validated' : '⚠ Pending' }}
                  </span>
                  <span class="text-sm font-medium text-gray-900">{{ result.structured_data?.vendor || 'Unknown Vendor' }}</span>
                  <span class="text-sm text-gray-500">{{ result.structured_data?.date || 'N/A' }}</span>
                </div>
                <div class="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span class="text-gray-500">Total:</span>
                    <span class="font-semibold text-gray-900 ml-2">${{ (result.structured_data?.total || 0).toFixed(2) }}</span>
                  </div>
                  <div>
                    <span class="text-gray-500">Category:</span>
                    <span class="text-gray-900 ml-2">{{ result.structured_data?.category || 'N/A' }}</span>
                  </div>
                  <div>
                    <span class="text-gray-500">Confidence:</span>
                    <span class="text-gray-900 ml-2">{{ (result.validation?.confidence * 100).toFixed(1) }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex space-x-4 pt-4 border-t mt-6">
          <button @click="reset" class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-gray-200 text-gray-800 hover:bg-gray-300 active:bg-gray-400">
            Upload More
          </button>
        </div>
      </div>
    </div>

    <!-- Single Result (for backward compatibility) -->
    <div v-if="result && !batchResults" class="mt-6 space-y-6">
      <div class="border-t pt-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Processing Results</h3>
        
        <!-- Status Badge -->
        <div class="mb-4">
          <span
            :class="[
              'inline-flex items-center px-3 py-1 rounded-full text-sm font-medium',
              result.status === 'validated'
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            ]"
          >
            {{ result.status === 'validated' ? '✓ Validated' : '⚠ Pending Review' }}
          </span>
        </div>

        <!-- Structured Data -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label class="text-sm font-medium text-gray-500">Vendor</label>
            <p class="text-base text-gray-900">{{ result.structured_data?.vendor || 'N/A' }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-gray-500">Date</label>
            <p class="text-base text-gray-900">{{ result.structured_data?.date || 'N/A' }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-gray-500">Total</label>
            <p class="text-base text-gray-900 font-semibold">${{ (result.structured_data?.total?.toFixed(2) || '0.00') }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-gray-500">Category</label>
            <p class="text-base text-gray-900">{{ result.structured_data?.category || 'N/A' }}</p>
          </div>
          <div>
            <label class="text-sm font-medium text-gray-500">Confidence</label>
            <p class="text-base text-gray-900">{{ (result.validation?.confidence * 100).toFixed(1) }}%</p>
          </div>
        </div>

        <!-- Validation Issues -->
        <div v-if="result.validation?.issues?.length" class="mb-4">
          <label class="text-sm font-medium text-gray-500 mb-2 block">Issues</label>
          <ul class="list-disc list-inside space-y-1">
            <li v-for="issue in result.validation.issues" :key="issue" class="text-sm text-yellow-700">
              {{ issue }}
            </li>
          </ul>
        </div>

        <!-- Explanation -->
        <div class="mb-4">
          <label class="text-sm font-medium text-gray-500 mb-2 block">Explanation</label>
          <p class="text-sm text-gray-700 bg-gray-50 p-4 rounded-lg">{{ result.explanation }}</p>
        </div>

        <!-- Recommendations -->
        <div v-if="result.recommendations?.length" class="mb-4">
          <label class="text-sm font-medium text-gray-500 mb-2 block">Recommendations</label>
          <ul class="list-disc list-inside space-y-1">
            <li v-for="rec in result.recommendations" :key="rec" class="text-sm text-gray-700">
              {{ rec }}
            </li>
          </ul>
        </div>

        <!-- Actions -->
        <div class="flex space-x-4 pt-4 border-t">
          <button @click="reset" class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-gray-200 text-gray-800 hover:bg-gray-300 active:bg-gray-400">Upload Another</button>
          <button
            v-if="result.status !== 'validated'"
            @click="approveEntry"
            class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800"
          >
            Approve & Add to Ledger
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api/client'

const emit = defineEmits(['receipt-processed'])

const fileInput = ref(null)
const isDragging = ref(false)
const processing = ref(false)
const processingMessage = ref('')
const progress = ref(0)
const result = ref(null)
const batchResults = ref(null)
const ocrEngine = ref('easyocr')
const processingFileCount = ref(0)
const currentFileIndex = ref(0)

const handleDrop = (e) => {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files)
  if (files.length > 0) {
    processFiles(files)
  }
}

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  if (files.length > 0) {
    processFiles(files)
  }
}

const processFiles = async (files) => {
  if (files.length === 0) return

  processing.value = true
  processingFileCount.value = files.length
  currentFileIndex.value = 0
  processingMessage.value = files.length === 1 ? 'Processing file...' : `Processing ${files.length} files...`
  progress.value = 10

  try {
    if (files.length === 1) {
      // Single file - use single endpoint
      processingMessage.value = 'Extracting text with OCR...'
      progress.value = 20

      processingMessage.value = 'Structuring data...'
      progress.value = 40

      processingMessage.value = 'Checking for duplicates...'
      progress.value = 60

      processingMessage.value = 'Validating with LLM...'
      progress.value = 80

      const response = await api.processReceipt(files[0], ocrEngine.value)
      result.value = response.data
      batchResults.value = null
      progress.value = 100

      processingMessage.value = 'Complete!'
      emit('receipt-processed', result.value)
    } else {
      // Multiple files - use batch endpoint
      processingMessage.value = `Processing ${files.length} files in batch...`
      progress.value = 30

      const response = await api.processReceiptsBatch(files, ocrEngine.value)
      batchResults.value = response.data
      result.value = null
      progress.value = 100

      processingMessage.value = `Complete! ${response.data.successful} successful, ${response.data.failed} failed`
      emit('receipt-processed', batchResults.value)
    }

    setTimeout(() => {
      processing.value = false
    }, 500)
  } catch (error) {
    console.error('Error processing receipt(s):', error)
    alert('Error processing receipt(s): ' + (error.response?.data?.detail || error.message))
    processing.value = false
    progress.value = 0
    processingFileCount.value = 0
  }
}

const approveEntry = async () => {
  if (!result.value?.record_id) return

  try {
    await api.approveLedgerEntry(result.value.record_id)
    result.value.status = 'validated'
    alert('Entry approved and added to ledger!')
  } catch (error) {
    console.error('Error approving entry:', error)
    alert('Error approving entry: ' + (error.response?.data?.detail || error.message))
  }
}

const reset = () => {
  result.value = null
  batchResults.value = null
  processing.value = false
  progress.value = 0
  processingFileCount.value = 0
  currentFileIndex.value = 0
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}
</script>
