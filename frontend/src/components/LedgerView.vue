<template>
  <div class="space-y-6">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="text-sm font-medium text-gray-500">Total Entries</div>
        <div class="text-2xl font-bold text-gray-900 mt-2">{{ stats.total_entries || 0 }}</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="text-sm font-medium text-gray-500">Total Amount</div>
        <div class="text-2xl font-bold text-gray-900 mt-2">${{ (stats.total_amount || 0).toFixed(2) }}</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="text-sm font-medium text-gray-500">Validated</div>
        <div class="text-2xl font-bold text-green-600 mt-2">{{ stats.validated_entries || 0 }}</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div class="text-sm font-medium text-gray-500">Pending</div>
        <div class="text-2xl font-bold text-yellow-600 mt-2">{{ stats.pending_entries || 0 }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Status</label>
          <select v-model="filters.status" @change="loadLedger" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all">
            <option value="">All</option>
            <option value="validated">Validated</option>
            <option value="pending">Pending</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Vendor</label>
          <input
            v-model="filters.vendor"
            @input="debounceLoadLedger"
            type="text"
            placeholder="Search vendor..."
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
          />
        </div>
        <div class="flex items-end">
          <button @click="clearFilters" class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-gray-200 text-gray-800 hover:bg-gray-300 active:bg-gray-400 w-full">Clear Filters</button>
        </div>
      </div>
    </div>

    <!-- Ledger Table -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Vendor</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="entry in ledgerEntries" :key="entry.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ entry.date || 'N/A' }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ entry.vendor || 'N/A' }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${{ (entry.amount || 0).toFixed(2) }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">${{ (entry.total || 0).toFixed(2) }}</td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                    entry.status === 'validated'
                      ? 'bg-green-100 text-green-800'
                      : entry.status === 'pending'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  ]"
                >
                  {{ entry.status }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ entry.validation_confidence ? (entry.validation_confidence * 100).toFixed(1) + '%' : 'N/A' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <div class="flex items-center gap-2">
                  <button
                    @click="viewDetails(entry)"
                    class="text-primary-600 hover:text-primary-800 font-medium"
                  >
                    View
                  </button>
                  <div v-if="entry.status === 'pending'" class="flex gap-1">
                    <button
                      @click="updateStatus(entry.record_id, 'validated')"
                      class="px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded hover:bg-green-200 transition-colors"
                      title="Validate"
                    >
                      ✓
                    </button>
                    <button
                      @click="updateStatus(entry.record_id, 'rejected')"
                      class="px-2 py-1 text-xs font-medium text-red-700 bg-red-100 rounded hover:bg-red-200 transition-colors"
                      title="Reject"
                    >
                      ✕
                    </button>
                  </div>
                  <button
                    @click="confirmDelete(entry)"
                    class="px-2 py-1 text-xs font-medium text-red-700 bg-red-100 rounded hover:bg-red-200 transition-colors"
                    title="Delete"
                  >
                    🗑️
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="ledgerEntries.length === 0">
              <td colspan="7" class="px-6 py-8 text-center text-gray-500">
                No ledger entries found
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="entryToDelete"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="entryToDelete = null"
    >
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full">
        <div class="p-6">
          <h3 class="text-xl font-bold text-gray-900 mb-4">Confirm Delete</h3>
          <p class="text-gray-700 mb-6">
            Are you sure you want to delete this transaction? This will permanently remove it from both the MySQL database and the vector database. This action cannot be undone.
          </p>
          <div class="flex gap-3 justify-end">
            <button
              @click="entryToDelete = null"
              class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-gray-200 text-gray-800 hover:bg-gray-300"
            >
              Cancel
            </button>
            <button
              @click="deleteEntry(entryToDelete.record_id)"
              class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-red-600 text-white hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Entry Details Modal -->
    <div
      v-if="selectedEntry"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="selectedEntry = null"
    >
      <div class="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-6">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-2xl font-bold text-gray-900">Entry Details</h3>
            <button @click="selectedEntry = null" class="text-gray-400 hover:text-gray-600">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-sm font-medium text-gray-500">Vendor</label>
                <p class="text-base text-gray-900">{{ selectedEntry.vendor || 'N/A' }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500">Date</label>
                <p class="text-base text-gray-900">{{ selectedEntry.date || 'N/A' }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500">Amount</label>
                <p class="text-base text-gray-900">${{ (selectedEntry.amount || 0).toFixed(2) }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500">Total</label>
                <p class="text-base text-gray-900 font-semibold">${{ (selectedEntry.total || 0).toFixed(2) }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500">Invoice Number</label>
                <p class="text-base text-gray-900">{{ selectedEntry.invoice_number || 'N/A' }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-500">Payment Method</label>
                <p class="text-base text-gray-900">{{ selectedEntry.payment_method || 'N/A' }}</p>
              </div>
            </div>

            <div v-if="selectedEntry.description">
              <label class="text-sm font-medium text-gray-500">Description</label>
              <p class="text-base text-gray-900">{{ selectedEntry.description }}</p>
            </div>

            <div v-if="selectedEntry.validation_issues?.length">
              <label class="text-sm font-medium text-gray-500">Validation Issues</label>
              <ul class="list-disc list-inside space-y-1 mt-2">
                <li v-for="issue in selectedEntry.validation_issues" :key="issue" class="text-sm text-yellow-700">
                  {{ issue }}
                </li>
              </ul>
            </div>

            <div v-if="selectedEntry.status === 'pending'" class="mt-6 pt-6 border-t border-gray-200">
              <div class="flex gap-3">
                <button
                  @click="updateStatus(selectedEntry.record_id, 'validated')"
                  class="flex-1 px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-green-600 text-white hover:bg-green-700"
                >
                  Validate
                </button>
                <button
                  @click="updateStatus(selectedEntry.record_id, 'rejected')"
                  class="flex-1 px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-red-600 text-white hover:bg-red-700"
                >
                  Reject
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const ledgerEntries = ref([])
const stats = ref({})
const selectedEntry = ref(null)
const entryToDelete = ref(null)
const filters = ref({
  status: '',
  vendor: ''
})
const loading = ref(false)

let debounceTimer = null

const loadLedger = async () => {
  try {
    const response = await api.getLedger(0, 100, filters.value.status || null, filters.value.vendor || null)
    ledgerEntries.value = response.data
  } catch (error) {
    console.error('Error loading ledger:', error)
  }
}

const loadStats = async () => {
  try {
    const response = await api.getStats()
    stats.value = response.data
  } catch (error) {
    console.error('Error loading stats:', error)
  }
}

const debounceLoadLedger = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadLedger, 500)
}

const clearFilters = () => {
  filters.value = { status: '', vendor: '' }
  loadLedger()
}

const viewDetails = async (entry) => {
  try {
    const response = await api.getLedgerEntry(entry.record_id)
    selectedEntry.value = response.data
  } catch (error) {
    console.error('Error loading entry details:', error)
    selectedEntry.value = entry
  }
}

const updateStatus = async (recordId, newStatus) => {
  if (loading.value) return
  loading.value = true
  try {
    await api.updateLedgerEntryStatus(recordId, newStatus)
    // Reload ledger and stats
    await loadLedger()
    await loadStats()
    // Close modal if open
    if (selectedEntry.value && selectedEntry.value.record_id === recordId) {
      selectedEntry.value.status = newStatus
    }
    alert(`Transaction status updated to ${newStatus}`)
  } catch (error) {
    console.error('Error updating status:', error)
    alert('Failed to update status: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const confirmDelete = (entry) => {
  entryToDelete.value = entry
}

const deleteEntry = async (recordId) => {
  if (loading.value) return
  loading.value = true
  try {
    await api.deleteLedgerEntry(recordId)
    // Reload ledger and stats
    await loadLedger()
    await loadStats()
    // Close modals
    entryToDelete.value = null
    if (selectedEntry.value && selectedEntry.value.record_id === recordId) {
      selectedEntry.value = null
    }
    alert('Transaction deleted successfully')
  } catch (error) {
    console.error('Error deleting entry:', error)
    alert('Failed to delete transaction: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadLedger()
  loadStats()
})
</script>

