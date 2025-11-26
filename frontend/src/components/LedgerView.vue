<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h2 class="text-xl lg:text-2xl font-bold text-gray-800">Transaction Ledger</h2>
        <p class="text-sm lg:text-base text-gray-500 mt-1">Manage and track your financial records</p>
      </div>
      <div class="flex gap-2 sm:gap-3">
        <button
          class="px-3 sm:px-4 py-2 bg-white/50 hover:bg-white/80 text-gray-700 rounded-xl text-sm font-medium transition-all duration-200 border border-white/40 shadow-sm backdrop-blur-sm">
          <span class="hidden sm:inline">Export CSV</span>
          <span class="sm:hidden">📊</span>
        </button>
        <button
          class="px-3 sm:px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-xl text-sm font-medium transition-all duration-200 shadow-lg shadow-gray-900/20">
          <span class="hidden sm:inline">Add Manual Entry</span>
          <span class="sm:hidden">+</span>
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-6">
      <div
        class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-4 lg:p-6 shadow-lg shadow-gray-200/20 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-gray-500 uppercase tracking-wider">Total</div>
        <div class="text-2xl lg:text-3xl font-bold text-gray-800 mt-2">{{ stats.total_entries || 0 }}</div>
      </div>
      <div
        class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-4 lg:p-6 shadow-lg shadow-gray-200/20 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-gray-500 uppercase tracking-wider">Amount</div>
        <div class="text-2xl lg:text-3xl font-bold text-gray-800 mt-2">${{ (stats.total_amount || 0).toFixed(2) }}</div>
        <div class="text-xs text-gray-400 mt-1">USD (converted)</div>
      </div>
      <div
        class="bg-green-50/40 backdrop-blur-md rounded-2xl border border-green-100/40 p-4 lg:p-6 shadow-lg shadow-green-900/5 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-green-600 uppercase tracking-wider">Validated</div>
        <div class="text-2xl lg:text-3xl font-bold text-green-700 mt-2">{{ stats.validated_entries || 0 }}</div>
      </div>
      <div
        class="bg-yellow-50/40 backdrop-blur-md rounded-2xl border border-yellow-100/40 p-4 lg:p-6 shadow-lg shadow-yellow-900/5 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-yellow-600 uppercase tracking-wider">Pending</div>
        <div class="text-2xl lg:text-3xl font-bold text-yellow-700 mt-2">{{ stats.pending_entries || 0 }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div
      class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-4 lg:p-6 shadow-lg shadow-gray-200/20">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-6">
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Status</label>
          <div class="relative">
            <select v-model="filters.status" @change="loadLedger"
              class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all appearance-none cursor-pointer">
              <option value="">All Statuses</option>
              <option value="validated">Validated</option>
              <option value="pending">Pending</option>
              <option value="rejected">Rejected</option>
            </select>
            <div class="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none text-gray-500">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
              </svg>
            </div>
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Vendor</label>
          <div class="relative">
            <input v-model="filters.vendor" @input="debounceLoadLedger" type="text" placeholder="Search vendor..."
              class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all pl-10" />
            <div class="absolute inset-y-0 left-0 flex items-center px-3 pointer-events-none text-gray-400">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
              </svg>
            </div>
          </div>
        </div>
        <div class="flex items-end">
          <button @click="clearFilters"
            class="px-6 py-3 rounded-xl font-medium transition-all duration-200 bg-gray-100/50 hover:bg-gray-200/50 text-gray-600 w-full border border-transparent hover:border-gray-200">
            Clear Filters
          </button>
        </div>
      </div>
    </div>

    <!-- Ledger Table -->
    <div
      class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 overflow-hidden shadow-xl shadow-gray-200/20">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200/50">
          <thead class="bg-gray-50/50">
            <tr>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-8"></th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Vendor</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Amount</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Total</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Confidence
              </th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200/50">
            <tr v-for="entry in ledgerEntries" :key="entry.id"
              class="hover:bg-white/40 transition-colors duration-150 cursor-pointer"
              @click="$emit('select-transaction', entry.record_id)">
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <button class="p-1 hover:bg-gray-200/50 rounded transition-all">
                  <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                  </svg>
                </button>
              </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 font-medium">{{ entry.date || 'N/A' }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-semibold">{{ entry.vendor || 'N/A' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{{ formatCurrency(entry.amount, entry.currency) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">{{ formatCurrency(entry.total, entry.currency) }}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span :class="[
                    'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border',
                    entry.status === 'validated'
                      ? 'bg-green-50/50 text-green-700 border-green-200/50'
                      : entry.status === 'pending'
                        ? 'bg-yellow-50/50 text-yellow-700 border-yellow-200/50'
                        : 'bg-red-50/50 text-red-700 border-red-200/50'
                  ]">
                    <span class="w-1.5 h-1.5 rounded-full mr-1.5" :class="{
                      'bg-green-500': entry.status === 'validated',
                      'bg-yellow-500': entry.status === 'pending',
                      'bg-red-500': entry.status === 'rejected'
                    }"></span>
                    {{ entry.status.charAt(0).toUpperCase() + entry.status.slice(1) }}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                  <div class="flex items-center gap-2">
                    <div class="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                      <div class="h-full rounded-full transition-all duration-500" :class="{
                        'bg-green-500': (entry.validation_confidence || 0) > 0.8,
                        'bg-yellow-500': (entry.validation_confidence || 0) > 0.5 && (entry.validation_confidence || 0) <= 0.8,
                        'bg-red-500': (entry.validation_confidence || 0) <= 0.5
                      }" :style="{ width: (entry.validation_confidence || 0) * 100 + '%' }"></div>
                    </div>
                    <span>{{ entry.validation_confidence ? Math.round(entry.validation_confidence * 100) + '%' : 'N/A'
                    }}</span>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm" @click.stop>
                  <div class="flex items-center gap-2">
                    <button @click="viewDetails(entry)"
                      class="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-all"
                      title="View Details">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z">
                        </path>
                      </svg>
                    </button>
                    <div v-if="entry.status === 'pending'" class="flex gap-1">
                      <button @click="updateStatus(entry.record_id, 'validated')"
                        class="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-all" title="Validate">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7">
                          </path>
                        </svg>
                      </button>
                      <button @click="updateStatus(entry.record_id, 'rejected')"
                        class="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-all" title="Reject">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                      </button>
                    </div>
                    <button @click="confirmDelete(entry)"
                      class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all"
                      title="Delete">
                      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16">
                        </path>
                      </svg>
                    </button>
                  </div>
                </td>
            </tr>

            <tr v-if="ledgerEntries.length === 0">
              <td colspan="8" class="px-6 py-12 text-center">
                <div class="flex flex-col items-center justify-center text-gray-400">
                  <svg class="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01">
                    </path>
                  </svg>
                  <p class="text-lg font-medium">No transactions found</p>
                  <p class="text-sm mt-1">Upload a receipt to get started</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="entryToDelete"
      class="fixed inset-0 bg-gray-900/40 backdrop-blur-sm flex items-center justify-center z-[60] p-4 transition-all duration-300"
      @click.self="entryToDelete = null">
      <div
        class="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl max-w-md w-full border border-white/50 overflow-hidden transform scale-100 transition-all">
        <div class="p-8">
          <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z">
              </path>
            </svg>
          </div>
          <h3 class="text-xl font-bold text-gray-900 text-center mb-2">Delete Transaction?</h3>
          <p class="text-gray-600 text-center mb-8">
            This action cannot be undone. This will permanently delete the transaction from your ledger.
          </p>
          <div class="flex gap-3">
            <button @click="entryToDelete = null"
              class="flex-1 px-4 py-3 rounded-xl font-medium transition-all duration-200 bg-gray-100 hover:bg-gray-200 text-gray-700">
              Cancel
            </button>
            <button @click="deleteEntry(entryToDelete.record_id)"
              class="flex-1 px-4 py-3 rounded-xl font-medium transition-all duration-200 bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/20">
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Entry Details Modal -->
    <div v-if="selectedEntry"
      class="fixed inset-0 bg-gray-900/40 backdrop-blur-sm flex items-center justify-center z-[60] p-4 transition-all duration-300 overflow-y-auto"
      @click.self="selectedEntry = null">
      <div
        class="bg-white/90 backdrop-blur-xl rounded-2xl lg:rounded-3xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-white/50 my-4">
        <div class="p-8">
          <div class="flex justify-between items-start mb-8">
            <div>
              <h3 class="text-2xl font-bold text-gray-900">Transaction Details</h3>
              <p class="text-gray-500 text-sm mt-1">ID: {{ selectedEntry.record_id }}</p>
            </div>
            <button @click="selectedEntry = null"
              class="p-2 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors">
              <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="space-y-8">
            <!-- Key Details Grid -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 lg:gap-6">
              <div class="bg-white/50 rounded-2xl p-4 border border-white/50">
                <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Vendor</label>
                <p class="text-lg font-semibold text-gray-900 mt-1">{{ selectedEntry.vendor || 'N/A' }}</p>
              </div>
              <div class="bg-white/50 rounded-2xl p-4 border border-white/50">
                <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Date</label>
                <p class="text-lg font-semibold text-gray-900 mt-1">{{ selectedEntry.date || 'N/A' }}</p>
              </div>
              <div class="bg-white/50 rounded-2xl p-4 border border-white/50">
                <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Total Amount</label>
                <p class="text-2xl font-bold text-gray-900 mt-1">${{ (selectedEntry.total || 0).toFixed(2) }}</p>
              </div>
              <div class="bg-white/50 rounded-2xl p-4 border border-white/50">
                <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Payment Method</label>
                <p class="text-lg font-semibold text-gray-900 mt-1">{{ selectedEntry.payment_method || 'N/A' }}</p>
              </div>
            </div>

            <div v-if="selectedEntry.description" class="bg-white/50 rounded-2xl p-5 border border-white/50">
              <label class="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2">Description</label>
              <p class="text-gray-700 leading-relaxed">{{ selectedEntry.description }}</p>
            </div>

            <!-- Items Table -->
            <div v-if="selectedEntry.items && selectedEntry.items.length > 0">
              <label class="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-3">Line Items</label>
              <div class="bg-white/50 rounded-2xl border border-white/50 overflow-hidden">
                <table class="min-w-full divide-y divide-gray-200/50">
                  <thead class="bg-gray-50/50">
                    <tr>
                      <th class="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Item</th>
                      <th class="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Qty</th>
                      <th class="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Price</th>
                      <th class="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-200/50">
                    <tr v-for="item in selectedEntry.items" :key="item.id" class="hover:bg-white/40">
                      <td class="px-5 py-3 text-sm text-gray-900 font-medium">{{ item.name }}</td>
                      <td class="px-5 py-3 text-sm text-gray-600 text-right">{{ item.quantity }}</td>
                      <td class="px-5 py-3 text-sm text-gray-600 text-right">${{ (item.unit_price || 0).toFixed(2) }}
                      </td>
                      <td class="px-5 py-3 text-sm text-gray-900 text-right font-bold">${{ (item.line_total ||
                        0).toFixed(2)
                      }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-if="selectedEntry.validation_issues?.length"
              class="bg-yellow-50/50 rounded-2xl p-5 border border-yellow-100">
              <label class="text-xs font-bold text-yellow-600 uppercase tracking-wider block mb-2">Validation
                Issues</label>
              <ul class="space-y-2">
                <li v-for="issue in selectedEntry.validation_issues" :key="issue"
                  class="flex items-start gap-2 text-sm text-yellow-800">
                  <svg class="w-5 h-5 text-yellow-500 flex-shrink-0" fill="none" stroke="currentColor"
                    viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z">
                    </path>
                  </svg>
                  <span>{{ issue }}</span>
                </li>
              </ul>
            </div>

            <div v-if="selectedEntry.status === 'pending'" class="pt-6 border-t border-gray-200/50 flex gap-4">
              <button @click="updateStatus(selectedEntry.record_id, 'validated')"
                class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-600/20">
                Validate Transaction
              </button>
              <button @click="updateStatus(selectedEntry.record_id, 'rejected')"
                class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/20">
                Reject Transaction
              </button>
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
  } catch (error) {
    console.error('Error deleting entry:', error)
    alert('Failed to delete transaction: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const formatCurrency = (amount, currency = 'USD') => {
  const symbols = {
    'USD': '$',
    'IDR': 'Rp',
    'ZAR': 'R',
    'EUR': '€',
    'GBP': '£'
  }
  
  const symbol = symbols[currency] || currency + ' '
  const value = amount || 0
  
  // No decimals for IDR and ZAR (whole number currencies)
  if (currency === 'IDR' || currency === 'ZAR') {
    return `${symbol}${value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
  }
  
  return `${symbol}${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

onMounted(() => {
  loadLedger()
  loadStats()
})
</script>
