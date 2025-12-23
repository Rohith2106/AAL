<template>
  <div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-3xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
      <div class="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h2 class="text-2xl font-bold text-gray-800">Claim Right Details</h2>
        <button
          @click="$emit('close')"
          class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-gray-900"></div>
        <p class="mt-4 text-gray-600">Loading claim right...</p>
      </div>

      <div v-else-if="claimRight" class="p-6 space-y-6">
        <!-- Header Info -->
        <div class="grid grid-cols-2 gap-6">
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Claim Type</div>
            <div class="flex items-center gap-2">
              <span
                :class="[
                  'px-3 py-1 rounded-lg text-sm font-semibold',
                  claimRight.claim_type === 'ASSET_CLAIM'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-red-100 text-red-700'
                ]"
              >
                {{ claimRight.claim_type === 'ASSET_CLAIM' ? 'Asset Claim' : 'Liability Claim' }}
              </span>
              <span
                :class="[
                  'px-3 py-1 rounded-lg text-sm font-semibold',
                  claimRight.status === 'active'
                    ? 'bg-blue-100 text-blue-700'
                    : claimRight.status === 'completed'
                    ? 'bg-gray-100 text-gray-700'
                    : 'bg-yellow-100 text-yellow-700'
                ]"
              >
                {{ claimRight.status }}
              </span>
            </div>
          </div>
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Description</div>
            <div class="text-lg font-semibold text-gray-800">{{ claimRight.description || 'Untitled Claim Right' }}</div>
          </div>
        </div>

        <!-- Financial Summary -->
        <div class="grid grid-cols-3 gap-4">
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Total Amount</div>
            <div class="text-2xl font-bold text-gray-800">${{ formatCurrency(claimRight.total_amount) }}</div>
          </div>
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Amortized</div>
            <div class="text-2xl font-bold text-green-600">${{ formatCurrency(claimRight.amortized_amount) }}</div>
            <div class="text-xs text-gray-500 mt-1">
              {{ ((claimRight.amortized_amount / claimRight.total_amount) * 100).toFixed(1) }}%
            </div>
          </div>
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Remaining</div>
            <div class="text-2xl font-bold text-orange-600">${{ formatCurrency(claimRight.remaining_amount) }}</div>
            <div class="text-xs text-gray-500 mt-1">
              {{ ((claimRight.remaining_amount / claimRight.total_amount) * 100).toFixed(1) }}%
            </div>
          </div>
        </div>

        <!-- Period Info -->
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Start Date</div>
            <div class="text-lg font-semibold text-gray-800">{{ formatDate(claimRight.start_date) }}</div>
          </div>
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">End Date</div>
            <div class="text-lg font-semibold text-gray-800">{{ formatDate(claimRight.end_date) }}</div>
          </div>
        </div>

        <!-- Additional Info -->
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Frequency</div>
            <div class="text-lg font-semibold text-gray-800 capitalize">{{ claimRight.frequency }}</div>
          </div>
          <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
            <div class="text-sm text-gray-500 font-medium mb-2">Created At</div>
            <div class="text-lg font-semibold text-gray-800">{{ formatDateTime(claimRight.created_at) }}</div>
          </div>
        </div>

        <!-- Cancellation Info -->
        <div v-if="claimRight.cancellation_date" class="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <div class="font-semibold text-yellow-800 mb-1">Cancelled</div>
          <div class="text-sm text-yellow-700">
            Date: {{ formatDate(claimRight.cancellation_date) }}
          </div>
          <div v-if="claimRight.cancellation_reason" class="text-sm text-yellow-700 mt-1">
            Reason: {{ claimRight.cancellation_reason }}
          </div>
        </div>

        <!-- Amortization Schedule -->
        <div v-if="claimRight.schedule" class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 shadow-xl overflow-hidden">
          <div class="p-6 border-b border-gray-200">
            <h3 class="text-lg font-bold text-gray-800">Amortization Schedule</h3>
            <p class="text-sm text-gray-500 mt-1">
              {{ claimRight.schedule.total_periods }} periods • ${{ formatCurrency(claimRight.schedule.amount_per_period) }} per period
            </p>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Period</th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Start Date</th>
                  <th class="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">End Date</th>
                  <th class="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase">Amount</th>
                  <th class="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr
                  v-for="entry in claimRight.schedule.entries"
                  :key="entry.id"
                  class="hover:bg-gray-50 transition-colors"
                >
                  <td class="px-4 py-3 text-sm font-medium text-gray-800">{{ entry.period_number }}</td>
                  <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(entry.period_start) }}</td>
                  <td class="px-4 py-3 text-sm text-gray-600">{{ formatDate(entry.period_end) }}</td>
                  <td class="px-4 py-3 text-sm font-semibold text-gray-800 text-right">${{ formatCurrency(entry.amount) }}</td>
                  <td class="px-4 py-3 text-center">
                    <span
                      :class="[
                        'px-2 py-1 rounded-lg text-xs font-semibold',
                        entry.status === 'POSTED'
                          ? 'bg-green-100 text-green-700'
                          : entry.status === 'PENDING'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-700'
                      ]"
                    >
                      {{ entry.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-4 pt-6 border-t border-gray-200">
          <button
            v-if="claimRight.status === 'active'"
            @click="handleCancel"
            :disabled="cancelling"
            class="px-6 py-3 bg-yellow-600 hover:bg-yellow-700 text-white rounded-xl font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ cancelling ? 'Cancelling...' : 'Cancel Claim Right' }}
          </button>
          <button
            @click="$emit('close')"
            class="ml-auto px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold transition-all duration-200"
          >
            Close
          </button>
        </div>
      </div>

      <div v-else class="p-12 text-center">
        <p class="text-gray-500">Claim right not found</p>
        <button
          @click="$emit('close')"
          class="mt-4 px-6 py-3 bg-gray-900 hover:bg-gray-800 text-white rounded-xl font-semibold transition-all duration-200"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const props = defineProps({
  claimRightId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['close', 'updated', 'deleted'])

const claimRight = ref(null)
const loading = ref(false)
const cancelling = ref(false)

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

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const loadClaimRight = async () => {
  loading.value = true
  try {
    const response = await api.getClaimRight(props.claimRightId)
    claimRight.value = response.data
  } catch (error) {
    console.error('Error loading claim right:', error)
    alert('Failed to load claim right: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleCancel = async () => {
  if (!confirm('Are you sure you want to cancel this claim right? This action cannot be undone.')) {
    return
  }

  const reason = prompt('Please provide a reason for cancellation (optional):')
  cancelling.value = true

  try {
    await api.cancelClaimRight(props.claimRightId, reason || null)
    emit('updated')
    emit('close')
  } catch (error) {
    console.error('Error cancelling claim right:', error)
    alert('Failed to cancel claim right: ' + (error.response?.data?.detail || error.message))
  } finally {
    cancelling.value = false
  }
}

onMounted(() => {
  loadClaimRight()
})
</script>

