<template>
  <div class="space-y-6">
    <!-- Header with Back Button -->
    <div class="flex items-center gap-4">
      <button @click="$emit('back')"
        class="p-2 hover:bg-gray-100 rounded-xl transition-all duration-200">
        <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
      </button>
      <div>
        <h2 class="text-2xl font-bold text-gray-800">Transaction Details</h2>
        <p class="text-sm text-gray-500 mt-1">{{ entry?.record_id || 'Loading...' }}</p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="flex space-x-2">
        <div class="w-3 h-3 bg-gray-400 rounded-full animate-bounce"></div>
        <div class="w-3 h-3 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
        <div class="w-3 h-3 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
      </div>
    </div>

    <!-- Transaction Details -->
    <div v-else-if="entry" class="space-y-6">
      <!-- Info Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Vendor</label>
          <p class="text-lg font-semibold text-gray-900 mt-2">{{ entry.vendor || 'N/A' }}</p>
        </div>
        <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Date</label>
          <p class="text-lg font-semibold text-gray-900 mt-2">{{ entry.date || 'N/A' }}</p>
        </div>
        <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Total</label>
          <p class="text-2xl font-bold text-gray-900 mt-2">${{ (entry.total || 0).toFixed(2) }}</p>
        </div>
        <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">Status</label>
          <span :class="[
            'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border mt-2',
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
        </div>
      </div>

      <!-- Line Items Table -->
      <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 overflow-hidden shadow-xl">
        <div class="px-6 py-4 border-b border-gray-200/50 bg-gray-50/50">
          <h3 class="text-lg font-bold text-gray-800">Line Items</h3>
          <p class="text-sm text-gray-500 mt-1">{{ entry.items?.length || 0 }} items</p>
        </div>
        
        <div class="overflow-x-auto">
          <table v-if="entry.items && entry.items.length > 0" class="min-w-full divide-y divide-gray-200/50">
            <thead class="bg-gray-50/50">
              <tr>
                <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Item</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Quantity</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Unit Price</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200/50">
              <tr v-for="item in entry.items" :key="item.id" class="hover:bg-white/40 transition-colors">
                <td class="px-6 py-4 text-sm text-gray-900 font-medium">{{ item.name }}</td>
                <td class="px-6 py-4 text-sm text-gray-600 text-right">{{ item.quantity }}</td>
                <td class="px-6 py-4 text-sm text-gray-600 text-right">${{ (item.unit_price || 0).toFixed(2) }}</td>
                <td class="px-6 py-4 text-sm text-gray-900 text-right font-bold">${{ (item.line_total || 0).toFixed(2) }}</td>
              </tr>
            </tbody>
            <tfoot class="bg-gray-50/50">
              <tr>
                <td colspan="3" class="px-6 py-4 text-sm font-bold text-gray-800 text-right">Subtotal:</td>
                <td class="px-6 py-4 text-sm font-bold text-gray-900 text-right">${{ (entry.amount || 0).toFixed(2) }}</td>
              </tr>
              <tr v-if="entry.tax">
                <td colspan="3" class="px-6 py-4 text-sm font-bold text-gray-800 text-right">Tax:</td>
                <td class="px-6 py-4 text-sm font-bold text-gray-900 text-right">${{ (entry.tax || 0).toFixed(2) }}</td>
              </tr>
              <tr class="border-t-2 border-gray-300">
                <td colspan="3" class="px-6 py-4 text-base font-bold text-gray-800 text-right">Total:</td>
                <td class="px-6 py-4 text-base font-bold text-gray-900 text-right">${{ (entry.total || 0).toFixed(2) }}</td>
              </tr>
            </tfoot>
          </table>
          
          <div v-else class="text-center py-12 text-gray-500">
            <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
            </svg>
            <p class="text-lg font-medium">No line items available</p>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div v-if="entry.status === 'pending'" class="flex gap-4">
        <button @click="updateStatus('validated')"
          class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-600/20">
          Validate Transaction
        </button>
        <button @click="updateStatus('rejected')"
          class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/20">
          Reject Transaction
        </button>
      </div>

      <button @click="confirmDelete"
        class="w-full px-6 py-3 rounded-xl font-medium transition-all duration-200 bg-red-100 hover:bg-red-200 text-red-700 border border-red-200">
        Delete Transaction
      </button>
    </div>

    <!-- Error State -->
    <div v-else class="text-center py-12 text-gray-500">
      <p class="text-lg font-medium">Transaction not found</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'

const props = defineProps({
  recordId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['back', 'updated', 'deleted'])

const entry = ref(null)
const loading = ref(false)

const loadEntry = async () => {
  loading.value = true
  try {
    const response = await api.getLedgerEntry(props.recordId)
    entry.value = response.data
    
    // DEBUG: Log the response
    console.log('API Response:', response.data)
    console.log('Items array:', response.data.items)
    console.log('Items count:', response.data.items?.length || 0)
  } catch (error) {
    console.error('Error loading entry:', error)
  } finally {
    loading.value = false
  }
}

const updateStatus = async (newStatus) => {
  if (loading.value) return
  loading.value = true
  try {
    await api.updateLedgerEntryStatus(props.recordId, newStatus)
    entry.value.status = newStatus
    emit('updated')
  } catch (error) {
    console.error('Error updating status:', error)
    alert('Failed to update status: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const confirmDelete = () => {
  if (confirm('Are you sure you want to delete this transaction? This action cannot be undone.')) {
    deleteEntry()
  }
}

const deleteEntry = async () => {
  if (loading.value) return
  loading.value = true
  try {
    await api.deleteLedgerEntry(props.recordId)
    emit('deleted')
    emit('back')
  } catch (error) {
    console.error('Error deleting entry:', error)
    alert('Failed to delete transaction: ' + (error.response?.data?.detail || error.message))
    loading.value = false
  }
}

onMounted(() => {
  loadEntry()
})
</script>
