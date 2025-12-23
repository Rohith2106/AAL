<template>
  <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-3xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h2 class="text-2xl font-bold text-gray-800">Create Claim Right from Transaction</h2>
        <button
          @click="$emit('close')"
          class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="p-6 space-y-6">
        <!-- Transaction Info -->
        <div class="p-4 bg-gray-50 rounded-xl border border-gray-200">
          <div class="text-sm font-medium text-gray-500 mb-2">Transaction Details</div>
          <div class="space-y-1 text-sm">
            <div><strong>Vendor:</strong> {{ transactionData.vendor || 'N/A' }}</div>
            <div><strong>Amount:</strong> ${{ formatCurrency(transactionData.total || 0) }}</div>
            <div><strong>Date:</strong> {{ formatDate(transactionData.date) }}</div>
          </div>
        </div>

        <!-- Claim Type -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Claim Type <span class="text-red-500">*</span>
          </label>
          <div class="grid grid-cols-2 gap-4">
            <button
              type="button"
              @click="form.claim_type = 'ASSET_CLAIM'"
              :class="[
                'p-4 rounded-xl border-2 transition-all duration-200',
                form.claim_type === 'ASSET_CLAIM'
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-gray-400'
              ]"
            >
              <div class="text-2xl mb-2">📈</div>
              <div class="font-semibold text-gray-800">Asset Claim</div>
              <div class="text-sm text-gray-500 mt-1">Prepaid expenses</div>
            </button>
            <button
              type="button"
              @click="form.claim_type = 'LIABILITY_CLAIM'"
              :class="[
                'p-4 rounded-xl border-2 transition-all duration-200',
                form.claim_type === 'LIABILITY_CLAIM'
                  ? 'border-red-500 bg-red-50'
                  : 'border-gray-300 hover:border-gray-400'
              ]"
            >
              <div class="text-2xl mb-2">📉</div>
              <div class="font-semibold text-gray-800">Liability Claim</div>
              <div class="text-sm text-gray-500 mt-1">Deferred revenue</div>
            </button>
          </div>
        </div>

        <!-- Description -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Description <span class="text-red-500">*</span>
          </label>
          <input
            v-model="form.description"
            type="text"
            required
            :placeholder="`Claim right for ${transactionData.vendor || 'transaction'}`"
            class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          />
        </div>

        <!-- Total Amount -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Total Amount <span class="text-red-500">*</span>
          </label>
          <input
            v-model.number="form.total_amount"
            type="number"
            step="0.01"
            required
            min="0"
            :placeholder="transactionData.total?.toString() || '0.00'"
            class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          />
        </div>

        <!-- Start Date -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Start Date <span class="text-red-500">*</span>
          </label>
          <input
            v-model="form.start_date"
            type="date"
            required
            class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          />
        </div>

        <!-- End Date -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            End Date <span class="text-red-500">*</span>
          </label>
          <input
            v-model="form.end_date"
            type="date"
            required
            class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          />
        </div>

        <!-- Frequency -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Amortization Frequency <span class="text-red-500">*</span>
          </label>
          <select
            v-model="form.frequency"
            required
            class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          >
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="flex gap-4 pt-6 border-t border-gray-200">
          <button
            type="button"
            @click="$emit('close')"
            class="flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-200 bg-gray-100 hover:bg-gray-200 text-gray-700"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="loading || !form.claim_type || !form.description || !form.total_amount || !form.start_date || !form.end_date"
            class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-gray-900 hover:bg-gray-800 text-white shadow-lg shadow-gray-900/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ loading ? 'Creating...' : 'Create Claim Right' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../api/client'

const props = defineProps({
  ledgerEntryId: {
    type: Number,
    required: true
  },
  transactionData: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'created'])

const loading = ref(false)
const error = ref(null)

const form = reactive({
  claim_type: '',
  description: '',
  total_amount: null,
  start_date: '',
  end_date: '',
  frequency: 'monthly'
})

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount || 0)
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

onMounted(() => {
  // Pre-fill form with transaction data
  if (props.transactionData.total) {
    form.total_amount = props.transactionData.total
  }
  if (props.transactionData.date) {
    form.start_date = props.transactionData.date.split('T')[0]
    // Default end date to 1 year from start
    const start = new Date(form.start_date)
    const end = new Date(start)
    end.setFullYear(end.getFullYear() + 1)
    form.end_date = end.toISOString().split('T')[0]
  }
  if (props.transactionData.vendor) {
    form.description = `Claim right for ${props.transactionData.vendor}`
  }
})

const handleSubmit = async () => {
  if (!form.claim_type || !form.description || !form.total_amount || !form.start_date || !form.end_date) {
    error.value = 'Please fill in all required fields'
    return
  }

  if (new Date(form.start_date) >= new Date(form.end_date)) {
    error.value = 'End date must be after start date'
    return
  }

  loading.value = true
  error.value = null

  try {
    await api.createClaimRightFromLedger(
      props.ledgerEntryId,
      form.claim_type,
      form.start_date + 'T00:00:00Z',
      form.end_date + 'T23:59:59Z',
      form.frequency
    )
    emit('created')
  } catch (err) {
    console.error('Error creating claim right:', err)
    error.value = err.response?.data?.detail || err.message || 'Failed to create claim right'
  } finally {
    loading.value = false
  }
}
</script>

