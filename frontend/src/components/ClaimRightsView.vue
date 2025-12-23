<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h2 class="text-xl lg:text-2xl font-bold text-gray-800">Claim Rights & Amortization</h2>
        <p class="text-sm lg:text-base text-gray-500 mt-1">Manage IFRS-based long-term assets and liabilities</p>
      </div>
      <div class="flex gap-3">
        <button
          @click="showCreateModal = true"
          class="px-6 py-3 bg-gray-900 hover:bg-gray-800 text-white rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-gray-900/20 hover:scale-105"
        >
          + Create Claim Right
        </button>
        <button
          @click="showAccrualModal = true"
          class="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold transition-all duration-200 shadow-lg shadow-blue-600/20 hover:scale-105"
        >
          ⚡ Process Accruals
        </button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div v-if="summary" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
        <div class="text-sm text-gray-500 font-medium">Total Claims</div>
        <div class="text-3xl font-bold text-gray-800 mt-2">{{ summary.total_claims }}</div>
      </div>
      <div class="bg-green-50/60 backdrop-blur-md rounded-2xl border border-green-200/40 p-6 shadow-xl">
        <div class="text-sm text-green-600 font-medium">Asset Claims</div>
        <div class="text-3xl font-bold text-green-700 mt-2">{{ summary.asset_claims }}</div>
        <div class="text-sm text-green-600 mt-1">${{ formatCurrency(summary.total_asset_amount) }}</div>
      </div>
      <div class="bg-red-50/60 backdrop-blur-md rounded-2xl border border-red-200/40 p-6 shadow-xl">
        <div class="text-sm text-red-600 font-medium">Liability Claims</div>
        <div class="text-3xl font-bold text-red-700 mt-2">{{ summary.liability_claims }}</div>
        <div class="text-sm text-red-600 mt-1">${{ formatCurrency(summary.total_liability_amount) }}</div>
      </div>
      <div class="bg-yellow-50/60 backdrop-blur-md rounded-2xl border border-yellow-200/40 p-6 shadow-xl">
        <div class="text-sm text-yellow-600 font-medium">Pending Accruals</div>
        <div class="text-3xl font-bold text-yellow-700 mt-2">{{ summary.pending_accruals }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-xl">
      <div class="flex flex-wrap gap-4">
        <div class="flex-1 min-w-[200px]">
          <label class="block text-sm font-medium text-gray-700 mb-2">Claim Type</label>
          <select
            v-model="filters.claimType"
            @change="loadClaimRights"
            class="w-full px-4 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          >
            <option value="">All Types</option>
            <option value="ASSET_CLAIM">Asset Claims</option>
            <option value="LIABILITY_CLAIM">Liability Claims</option>
          </select>
        </div>
        <div class="flex-1 min-w-[200px]">
          <label class="block text-sm font-medium text-gray-700 mb-2">Status</label>
          <select
            v-model="filters.status"
            @change="loadClaimRights"
            class="w-full px-4 py-2 rounded-xl border border-gray-300 focus:ring-2 focus:ring-gray-900 focus:border-transparent"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Claim Rights List -->
    <div class="bg-white/60 backdrop-blur-md rounded-2xl border border-white/40 shadow-xl overflow-hidden">
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-gray-900"></div>
        <p class="mt-4 text-gray-600">Loading claim rights...</p>
      </div>
      <div v-else-if="claimRights.length === 0" class="p-12 text-center">
        <p class="text-gray-500 text-lg">No claim rights found</p>
        <button
          @click="showCreateModal = true"
          class="mt-4 px-6 py-3 bg-gray-900 hover:bg-gray-800 text-white rounded-xl font-semibold transition-all duration-200"
        >
          Create Your First Claim Right
        </button>
      </div>
      <div v-else class="divide-y divide-gray-200/50">
        <div
          v-for="claim in claimRights"
          :key="claim.id"
          @click="selectClaim(claim.id)"
          class="p-6 hover:bg-white/40 transition-all duration-200 cursor-pointer"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2">
                <span
                  :class="[
                    'px-3 py-1 rounded-lg text-xs font-semibold',
                    claim.claim_type === 'ASSET_CLAIM'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  ]"
                >
                  {{ claim.claim_type === 'ASSET_CLAIM' ? 'Asset' : 'Liability' }}
                </span>
                <span
                  :class="[
                    'px-3 py-1 rounded-lg text-xs font-semibold',
                    claim.status === 'active'
                      ? 'bg-blue-100 text-blue-700'
                      : claim.status === 'completed'
                      ? 'bg-gray-100 text-gray-700'
                      : 'bg-yellow-100 text-yellow-700'
                  ]"
                >
                  {{ claim.status }}
                </span>
              </div>
              <h3 class="text-lg font-semibold text-gray-800 mb-1">{{ claim.description || 'Untitled Claim Right' }}</h3>
              <p class="text-sm text-gray-500 mb-3">
                {{ formatDate(claim.start_date) }} - {{ formatDate(claim.end_date) }}
              </p>
              <div class="flex gap-6 text-sm">
                <div>
                  <span class="text-gray-500">Total:</span>
                  <span class="font-semibold text-gray-800 ml-2">${{ formatCurrency(claim.total_amount) }}</span>
                </div>
                <div>
                  <span class="text-gray-500">Amortized:</span>
                  <span class="font-semibold text-gray-800 ml-2">${{ formatCurrency(claim.amortized_amount) }}</span>
                </div>
                <div>
                  <span class="text-gray-500">Remaining:</span>
                  <span class="font-semibold text-gray-800 ml-2">${{ formatCurrency(claim.remaining_amount) }}</span>
                </div>
                <div>
                  <span class="text-gray-500">Frequency:</span>
                  <span class="font-semibold text-gray-800 ml-2 capitalize">{{ claim.frequency }}</span>
                </div>
              </div>
            </div>
            <div class="ml-4">
              <div class="w-24 h-24 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                <span class="text-3xl">
                  {{ claim.claim_type === 'ASSET_CLAIM' ? '📈' : '📉' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Claim Right Modal -->
    <CreateClaimRightModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="handleClaimRightCreated"
    />

    <!-- Process Accruals Modal -->
    <ProcessAccrualsModal
      v-if="showAccrualModal"
      @close="showAccrualModal = false"
      @processed="handleAccrualsProcessed"
    />

    <!-- Claim Right Detail Modal -->
    <ClaimRightDetail
      v-if="selectedClaimId"
      :claimRightId="selectedClaimId"
      @close="selectedClaimId = null"
      @updated="handleClaimRightUpdated"
      @deleted="handleClaimRightDeleted"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import CreateClaimRightModal from './CreateClaimRightModal.vue'
import ProcessAccrualsModal from './ProcessAccrualsModal.vue'
import ClaimRightDetail from './ClaimRightDetail.vue'

const claimRights = ref([])
const summary = ref(null)
const loading = ref(false)
const showCreateModal = ref(false)
const showAccrualModal = ref(false)
const selectedClaimId = ref(null)
const filters = ref({
  claimType: '',
  status: ''
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

const loadClaimRights = async () => {
  loading.value = true
  try {
    const response = await api.getClaimRights(
      filters.value.claimType || null,
      filters.value.status || null
    )
    claimRights.value = response.data
  } catch (error) {
    console.error('Error loading claim rights:', error)
    alert('Failed to load claim rights: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const loadSummary = async () => {
  try {
    const response = await api.getClaimRightsSummary()
    summary.value = response.data
  } catch (error) {
    console.error('Error loading summary:', error)
  }
}

const selectClaim = (id) => {
  selectedClaimId.value = id
}

const handleClaimRightCreated = () => {
  showCreateModal.value = false
  loadClaimRights()
  loadSummary()
}

const handleAccrualsProcessed = () => {
  showAccrualModal.value = false
  loadClaimRights()
  loadSummary()
}

const handleClaimRightUpdated = () => {
  selectedClaimId.value = null
  loadClaimRights()
  loadSummary()
}

const handleClaimRightDeleted = () => {
  selectedClaimId.value = null
  loadClaimRights()
  loadSummary()
}

onMounted(() => {
  loadClaimRights()
  loadSummary()
})
</script>

