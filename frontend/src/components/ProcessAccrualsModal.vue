<template>
  <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h2 class="text-2xl font-bold text-gray-800">Process Accruals</h2>
        <button
          @click="$emit('close')"
          class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="p-6 space-y-6">
        <!-- Info Box -->
        <div class="p-4 bg-blue-50 border border-blue-200 rounded-xl">
          <p class="text-sm text-blue-800">
            <strong>What does this do?</strong><br>
            Processes pending amortization entries for the specified period. This recognizes revenue/expense over time according to IFRS principles.
          </p>
        </div>

        <!-- Period Selection -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Period Start
            </label>
            <input
              v-model="form.period_start"
              type="date"
              class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Period End
            </label>
            <input
              v-model="form.period_end"
              type="date"
              class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />
          </div>
        </div>

        <!-- Dry Run Option -->
        <div class="flex items-center gap-3">
          <input
            v-model="form.dry_run"
            type="checkbox"
            id="dry-run"
            class="w-5 h-5 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
          />
          <label for="dry-run" class="text-sm font-medium text-gray-700">
            Dry Run (Preview only, don't post journal entries)
          </label>
        </div>

        <!-- Quick Actions -->
        <div class="grid grid-cols-3 gap-3">
          <button
            type="button"
            @click="setCurrentMonth"
            class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-sm font-medium text-gray-700 transition-colors"
          >
            Current Month
          </button>
          <button
            type="button"
            @click="setCurrentQuarter"
            class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-sm font-medium text-gray-700 transition-colors"
          >
            Current Quarter
          </button>
          <button
            type="button"
            @click="setCurrentYear"
            class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-sm font-medium text-gray-700 transition-colors"
          >
            Current Year
          </button>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          {{ error }}
        </div>

        <!-- Results -->
        <div v-if="result" class="p-4 bg-green-50 border border-green-200 rounded-xl">
          <h3 class="font-semibold text-green-800 mb-2">Accruals Processed Successfully</h3>
          <div class="space-y-1 text-sm text-green-700">
            <div>Entries Processed: <strong>{{ result.entries_processed }}</strong></div>
            <div>Total Amount: <strong>${{ formatCurrency(result.total_amount) }}</strong></div>
            <div>Asset Claims: <strong>{{ result.asset_claims }}</strong></div>
            <div>Liability Claims: <strong>{{ result.liability_claims }}</strong></div>
          </div>
          <div v-if="result.errors && result.errors.length > 0" class="mt-3 pt-3 border-t border-green-300">
            <div class="text-sm font-semibold text-red-700 mb-1">Errors:</div>
            <ul class="list-disc list-inside text-sm text-red-600">
              <li v-for="(err, idx) in result.errors" :key="idx">{{ err }}</li>
            </ul>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-4 pt-6 border-t border-gray-200">
          <button
            type="button"
            @click="$emit('close')"
            class="flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-200 bg-gray-100 hover:bg-gray-200 text-gray-700"
          >
            {{ result ? 'Close' : 'Cancel' }}
          </button>
          <button
            v-if="!result"
            @click="handleProcess"
            :disabled="loading || (!form.period_start && !form.period_end)"
            class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? 'Processing...' : 'Process Accruals' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { api } from '../api/client'

const emit = defineEmits(['close', 'processed'])

const loading = ref(false)
const error = ref(null)
const result = ref(null)

const form = reactive({
  period_start: '',
  period_end: '',
  dry_run: false
})

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount || 0)
}

const setCurrentMonth = () => {
  const now = new Date()
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  form.period_start = firstDay.toISOString().split('T')[0]
  form.period_end = lastDay.toISOString().split('T')[0]
}

const setCurrentQuarter = () => {
  const now = new Date()
  const quarter = Math.floor(now.getMonth() / 3)
  const firstDay = new Date(now.getFullYear(), quarter * 3, 1)
  const lastDay = new Date(now.getFullYear(), (quarter + 1) * 3, 0)
  form.period_start = firstDay.toISOString().split('T')[0]
  form.period_end = lastDay.toISOString().split('T')[0]
}

const setCurrentYear = () => {
  const now = new Date()
  const firstDay = new Date(now.getFullYear(), 0, 1)
  const lastDay = new Date(now.getFullYear(), 11, 31)
  form.period_start = firstDay.toISOString().split('T')[0]
  form.period_end = lastDay.toISOString().split('T')[0]
}

const handleProcess = async () => {
  loading.value = true
  error.value = null
  result.value = null

  try {
    const response = await api.processAccruals(
      form.period_start || null,
      form.period_end || null,
      form.dry_run
    )
    result.value = response.data
    if (!form.dry_run) {
      emit('processed')
    }
  } catch (err) {
    console.error('Error processing accruals:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to process accruals'
  } finally {
    loading.value = false
  }
}
</script>

