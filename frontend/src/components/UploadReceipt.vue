<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h2 class="text-xl lg:text-2xl font-bold text-gray-800">{{ t('upload.title') }}</h2>
        <p class="text-sm lg:text-base text-gray-500 mt-1">{{ t('upload.subtitle') }}</p>
      </div>
    </div>

    <!-- Upload Area -->
    <div class="bg-white/40 backdrop-blur-md rounded-3xl border border-white/40 p-8 shadow-xl shadow-gray-200/20">
      <div
        @drop.prevent="handleDrop"
        @dragover.prevent
        @dragenter.prevent
        :class="[
          'border-3 border-dashed rounded-2xl p-8 lg:p-16 text-center transition-all duration-300 group cursor-pointer',
          isDragging 
            ? 'border-primary-500 bg-primary-50/50 scale-[1.02]' 
            : 'border-gray-300 hover:border-primary-400 hover:bg-white/50'
        ]"
        @click="$refs.fileInput.click()"
      >
        <input
          ref="fileInput"
          type="file"
          accept="image/*,.pdf"
          multiple
          @change="handleFileSelect"
          class="hidden"
        />
        
        <div v-if="!processing && !batchResults" class="space-y-4">
          <div class="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto group-hover:bg-primary-50 transition-colors duration-300">
            <svg class="w-10 h-10 text-gray-400 group-hover:text-primary-500 transition-colors duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <p class="text-xl font-bold text-gray-700 group-hover:text-primary-600 transition-colors">
              {{ t('upload.dropHere') }}
            </p>
            <p class="text-gray-500 mt-2">{{ t('upload.browse') }}</p>
          </div>
          <div class="flex items-center justify-center gap-2 text-xs text-gray-400 uppercase tracking-wider font-medium mt-4">
            <span class="px-2 py-1 bg-gray-100 rounded">JPG</span>
            <span class="px-2 py-1 bg-gray-100 rounded">PNG</span>
            <span class="px-2 py-1 bg-gray-100 rounded">PDF</span>
          </div>
        </div>
        
        <!-- Processing -->
        <div v-if="processing" class="space-y-6">
          <div class="relative w-24 h-24 mx-auto">
            <div class="absolute inset-0 border-4 border-gray-200 rounded-full"></div>
            <div class="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
          </div>
          <div>
            <p class="text-xl font-bold text-gray-800">{{ currentLogMessage || processingMessage }}</p>
            <p v-if="processingFileCount > 0" class="text-gray-500 mt-2">
              Processing {{ currentFileIndex }} of {{ processingFileCount }} files...
            </p>
          </div>
          
          <!-- Log Messages -->
          <div v-if="logMessages.length > 0" class="w-full max-w-2xl mx-auto bg-gray-900/90 rounded-xl p-4 max-h-64 overflow-y-auto border border-gray-700/50">
            <div class="space-y-1">
              <div
                v-for="(log, index) in logMessages"
                :key="index"
                :class="[
                  'text-xs font-mono px-3 py-2 rounded-lg transition-all',
                  log.level === 'ERROR' ? 'text-red-300 bg-red-900/30 border border-red-800/50' :
                  log.level === 'WARNING' ? 'text-yellow-300 bg-yellow-900/30 border border-yellow-800/50' :
                  'text-green-300 bg-green-900/20 border border-green-800/30'
                ]"
              >
                <div class="flex items-start gap-2">
                  <span class="text-gray-500 text-[10px] mt-0.5 flex-shrink-0">
                    {{ log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '' }}
                  </span>
                  <span class="flex-1 break-words">{{ log.message || log.raw_message || '' }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div class="w-full max-w-md mx-auto bg-gray-100 rounded-full h-3 overflow-hidden">
            <div class="bg-primary-600 h-full rounded-full transition-all duration-500 ease-out" :style="{ width: progress + '%' }"></div>
          </div>
        </div>
      </div>

      <!-- OCR Engine Selection -->
      <div v-if="!processing && !batchResults" class="mt-8 space-y-4">
        <!-- Engine Selection -->
        <div class="flex flex-col items-center gap-2">
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('upload.ocrEngine') }}</span>
          <div class="inline-flex bg-gray-100/50 p-1 rounded-xl border border-gray-200/50">
            <button
              @click="ocrEngine = 'easyocr'"
              :class="[
                'px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                ocrEngine === 'easyocr'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              ]"
            >
              EasyOCR ({{ t('upload.recommended') }})
            </button>
            <button
              @click="ocrEngine = 'tesseract'"
              :class="[
                'px-6 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                ocrEngine === 'tesseract'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              ]"
            >
              Tesseract
            </button>
          </div>
        </div>
        
        <!-- OCR Language Selection -->
        <div class="flex flex-col items-center gap-2">
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('upload.ocrLanguage') }}</span>
          <div class="inline-flex bg-gray-100/50 p-1 rounded-xl border border-gray-200/50">
            <button
              @click="ocrLanguage = 'en'"
              :class="[
                'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-1',
                ocrLanguage === 'en'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              ]"
            >
              🇺🇸 {{ t('upload.english') }}
            </button>
            <button
              @click="ocrLanguage = 'ja'"
              :class="[
                'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-1',
                ocrLanguage === 'ja'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              ]"
            >
              🇯🇵 {{ t('upload.japanese') }}
            </button>
            <button
              @click="ocrLanguage = 'en_ja'"
              :class="[
                'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-1',
                ocrLanguage === 'en_ja'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              ]"
            >
              🌐 {{ t('upload.both') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Batch Results -->
    <div v-if="batchResults" class="bg-white/40 backdrop-blur-md rounded-3xl border border-white/40 p-8 shadow-xl shadow-gray-200/20">
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-xl font-bold text-gray-900">Processing Results</h3>
        <div class="flex gap-3">
          <span class="px-3 py-1 bg-green-100 text-green-700 rounded-lg text-sm font-medium">✓ {{ batchResults.successful }} successful</span>
          <span v-if="batchResults.failed > 0" class="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-sm font-medium">✗ {{ batchResults.failed }} failed</span>
        </div>
      </div>

      <div class="space-y-4">
        <div
          v-for="(result, index) in batchResults.results"
          :key="result.record_id"
          class="bg-white/60 rounded-xl p-4 border border-white/50 hover:shadow-md transition-all duration-200"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                result.status === 'validated' ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'
              ]">
                <svg v-if="result.status === 'validated'" class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                <svg v-else class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              </div>
              <div>
                <h4 class="font-bold text-gray-900">{{ result.structured_data?.vendor || 'Unknown Vendor' }}</h4>
                <p class="text-sm text-gray-500">{{ result.structured_data?.date || 'No date' }} • {{ result.structured_data?.category || 'Uncategorized' }}</p>
              </div>
            </div>
            <div class="text-right">
              <p class="text-lg font-bold text-gray-900">${{ (result.structured_data?.total || 0).toFixed(2) }}</p>
              <p class="text-xs text-gray-500 font-medium">Confidence: {{ (result.validation?.confidence * 100).toFixed(0) }}%</p>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-center mt-8">
        <button @click="reset" class="px-8 py-3 rounded-xl font-bold transition-all duration-200 bg-gray-900 text-white hover:bg-gray-800 shadow-lg shadow-gray-900/20 hover:scale-[1.02]">
          {{ t('upload.uploadMore') }}
        </button>
      </div>
    </div>

    <!-- Single Result -->
    <div v-if="result && !batchResults" class="bg-white/40 backdrop-blur-md rounded-3xl border border-white/40 p-8 shadow-xl shadow-gray-200/20">
      <div class="flex items-center justify-between mb-8">
        <h3 class="text-xl font-bold text-gray-900">Processing Result</h3>
        <span
          :class="[
            'px-4 py-2 rounded-xl text-sm font-bold',
            result.status === 'validated'
              ? 'bg-green-100 text-green-700'
              : 'bg-yellow-100 text-yellow-700'
          ]"
        >
          {{ result.status === 'validated' ? '✓ Validated' : '⚠ Pending Review' }}
        </span>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
        <!-- Receipt Preview Card -->
        <div class="bg-white/60 rounded-2xl p-6 border border-white/50 shadow-sm">
          <div class="flex justify-between items-start mb-6">
            <div>
              <p class="text-sm font-bold text-gray-400 uppercase tracking-wider">Vendor</p>
              <h4 class="text-2xl font-bold text-gray-900 mt-1">{{ result.structured_data?.vendor || 'N/A' }}</h4>
            </div>
            <div class="text-right">
              <p class="text-sm font-bold text-gray-400 uppercase tracking-wider">Total</p>
              <h4 class="text-2xl font-bold text-gray-900 mt-1">${{ (result.structured_data?.total?.toFixed(2) || '0.00') }}</h4>
            </div>
          </div>
          
          <div class="space-y-4">
            <div class="flex justify-between py-3 border-b border-gray-100">
              <span class="text-gray-500">Date</span>
              <span class="font-medium text-gray-900">{{ result.structured_data?.date || 'N/A' }}</span>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-100">
              <span class="text-gray-500">Category</span>
              <span class="font-medium text-gray-900">{{ result.structured_data?.category || 'N/A' }}</span>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-100">
              <span class="text-gray-500">Confidence</span>
              <span class="font-medium text-gray-900">{{ (result.validation?.confidence * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>

        <!-- Analysis Card -->
        <div class="space-y-6">
          <div v-if="result.validation?.issues?.length" class="bg-yellow-50/50 rounded-2xl p-6 border border-yellow-100">
            <h5 class="font-bold text-yellow-800 mb-3 flex items-center gap-2">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
              Validation Issues
            </h5>
            <ul class="space-y-2">
              <li v-for="issue in result.validation.issues" :key="issue" class="text-sm text-yellow-700 flex items-start gap-2">
                <span class="mt-1.5 w-1.5 h-1.5 bg-yellow-400 rounded-full flex-shrink-0"></span>
                {{ issue }}
              </li>
            </ul>
          </div>

          <div class="bg-white/60 rounded-2xl p-6 border border-white/50 shadow-sm">
            <h5 class="font-bold text-gray-900 mb-3">AI Analysis</h5>
            <p class="text-gray-600 text-sm leading-relaxed">{{ result.explanation }}</p>
          </div>
        </div>
      </div>

      <div class="flex gap-4 mt-8 pt-8 border-t border-gray-200/50">
        <button @click="reset" class="flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-200 bg-gray-100 hover:bg-gray-200 text-gray-700">
          Upload Another
        </button>
        <button
          v-if="result.status !== 'validated'"
          @click="approveEntry"
          class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-gray-900 text-white hover:bg-gray-800 shadow-lg shadow-gray-900/20"
        >
          Approve & Add to Ledger
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api/client'
import { useI18n } from '../i18n/i18n.js'

const { t } = useI18n()

const emit = defineEmits(['receipt-processed'])

const fileInput = ref(null)
const isDragging = ref(false)
const processing = ref(false)
const processingMessage = ref('')
const progress = ref(0)
const result = ref(null)
const batchResults = ref(null)
const ocrEngine = ref('easyocr')
const ocrLanguage = ref('en')
const processingFileCount = ref(0)
const currentFileIndex = ref(0)
const logMessages = ref([])
const currentLogMessage = ref('')
const currentRecordId = ref(null)
const eventSource = ref(null)

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

const connectToLogStream = (recordId) => {
  // Close existing connection if any
  if (eventSource.value) {
    eventSource.value.close()
  }
  
  logMessages.value = []
  currentRecordId.value = recordId
  
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
  eventSource.value = new EventSource(`${API_BASE_URL}/process-receipt/${recordId}/logs`)
  
  eventSource.value.onmessage = (event) => {
    try {
      const logEntry = JSON.parse(event.data)
      
      // Skip heartbeat messages
      if (logEntry.type === 'heartbeat') {
        return
      }
      
      // Extract meaningful message from log
      const message = logEntry.message || logEntry.raw_message || ''
      
      // Update current log message (show last meaningful log)
      if (message) {
        // Use the clean message if available, otherwise extract from raw
        if (logEntry.message) {
          currentLogMessage.value = logEntry.message
        } else {
          // Extract the actual log content after the logger name
          const parts = message.split(':')
          if (parts.length > 2) {
            currentLogMessage.value = parts.slice(2).join(':').trim()
          } else {
            currentLogMessage.value = message
          }
        }
      }
      
      // Add to log messages list (keep last 50)
      logMessages.value.push(logEntry)
      if (logMessages.value.length > 50) {
        logMessages.value.shift()
      }
      
      // Auto-scroll to bottom
      setTimeout(() => {
        const logContainer = document.querySelector('.overflow-y-auto')
        if (logContainer) {
          logContainer.scrollTop = logContainer.scrollHeight
        }
      }, 100)
    } catch (e) {
      console.error('Error parsing log entry:', e)
    }
  }
  
  eventSource.value.onerror = (error) => {
    console.error('EventSource error:', error)
    // Don't close on error - might be temporary
  }
}

const processFiles = async (files) => {
  if (files.length === 0) return

  processing.value = true
  processingFileCount.value = files.length
  currentFileIndex.value = 0
  processingMessage.value = files.length === 1 ? 'Processing file...' : `Processing ${files.length} files...`
  progress.value = 10
  logMessages.value = []
  currentLogMessage.value = ''

  try {
    if (files.length === 1) {
      // Single file - use single endpoint
      // Generate record_id first to connect to logs
      const recordId = `record_${Date.now().toString(36)}${Math.random().toString(36).substr(2, 9)}`
      currentRecordId.value = recordId
      
      // Connect to log stream BEFORE processing starts
      connectToLogStream(recordId)
      
      // Small delay to ensure connection is established
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Start processing with the record_id and language
      const response = await api.processReceipt(files[0], ocrEngine.value, recordId, ocrLanguage.value)
      result.value = response.data
      batchResults.value = null
      
      progress.value = 100
      processingMessage.value = 'Complete!'
      emit('receipt-processed', result.value)
      
      // Close log stream after a delay
      setTimeout(() => {
        if (eventSource.value) {
          eventSource.value.close()
          eventSource.value = null
        }
      }, 2000)
    } else {
      // Multiple files - use batch endpoint
      processingMessage.value = `Processing ${files.length} files in batch...`
      progress.value = 30

      const response = await api.processReceiptsBatch(files, ocrEngine.value, ocrLanguage.value)
      batchResults.value = response.data
      result.value = null
      progress.value = 100

      processingMessage.value = `Complete! ${response.data.successful} successful, ${response.data.failed} failed`
      emit('receipt-processed', batchResults.value)
    }

    setTimeout(() => {
      processing.value = false
      // Close log stream
      if (eventSource.value) {
        eventSource.value.close()
        eventSource.value = null
      }
    }, 500)
  } catch (error) {
    console.error('Error processing receipt(s):', error)
    alert('Error processing receipt(s): ' + (error.response?.data?.detail || error.message))
    processing.value = false
    progress.value = 0
    processingFileCount.value = 0
    // Close log stream on error
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
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
  logMessages.value = []
  currentLogMessage.value = ''
  currentRecordId.value = null
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}
</script>
