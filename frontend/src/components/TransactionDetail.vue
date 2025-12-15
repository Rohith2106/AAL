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
        <h2 class="text-2xl font-bold text-gray-800">{{ t('detail.title') }}</h2>
        <p class="text-sm text-gray-500 mt-1">{{ entry?.record_id || t('detail.loading') }}</p>
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
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">{{ t('detail.vendor') }}</label>
          <p class="text-lg font-semibold text-gray-900 mt-2">{{ entry.vendor || t('common.na') }}</p>
        </div>
        <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">{{ t('detail.date') }}</label>
          <p class="text-lg font-semibold text-gray-900 mt-2">{{ entry.date || t('common.na') }}</p>
        </div>
        <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">{{ t('detail.total') }}</label>
          <p class="text-2xl font-bold text-gray-900 mt-2">{{ formatCurrency(entry.total || 0, entry.currency) }}</p>
        </div>
        <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
          <label class="text-xs font-bold text-gray-400 uppercase tracking-wider">{{ t('detail.status') }}</label>
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

      <!-- Perspective-Aware Counterparty Analysis -->
      <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-6 shadow-lg">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-sm font-bold text-gray-700 uppercase tracking-wider">
              Transaction Perspective
            </h3>
            <p class="text-xs text-gray-500 mt-1" v-if="!perspectiveLoading && perspective">
              {{ perspective.transactionDirection }} · {{ perspective.documentRole }}
            </p>
          </div>
          <div v-if="perspective && perspective.confidence !== undefined" class="text-right">
            <p class="text-xs text-gray-500">Confidence</p>
            <p class="text-sm font-semibold text-gray-800">
              {{ (perspective.confidence * 100).toFixed(0) }}%
            </p>
          </div>
        </div>

        <div v-if="perspectiveLoading" class="flex items-center space-x-2 text-xs text-gray-500">
          <span class="w-2 h-2 rounded-full bg-gray-400 animate-pulse"></span>
          <span>Analyzing counterparty perspective…</span>
        </div>

        <div v-else-if="perspective" class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Direction</p>
            <p class="mt-0.5 font-medium text-gray-900">
              {{ perspective.transactionDirection === 'OUTFLOW' ? 'Outflow (we pay)' : 'Inflow (we receive)' }}
            </p>
          </div>
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Our Role</p>
            <p class="mt-0.5 font-medium text-gray-900">
              {{ perspective.ourRole }}
            </p>
          </div>
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Counterparty Role</p>
            <p class="mt-0.5 font-medium text-gray-900">
              {{ perspective.counterpartyRole }}
            </p>
          </div>
          <div>
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Counterparty</p>
            <p class="mt-0.5 font-medium text-gray-900">
              {{ perspective.counterpartyName || entry.vendor || t('common.na') }}
            </p>
          </div>
        </div>

        <div v-else class="text-xs text-gray-400">
          Perspective analysis not available for this transaction.
        </div>
      </div>

      <!-- Line Items Table -->
      <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 overflow-hidden shadow-xl">
        <div class="px-6 py-4 border-b border-gray-200/50 bg-gray-50/50">
          <h3 class="text-lg font-bold text-gray-800">{{ t('detail.lineItems') }}</h3>
          <p class="text-sm text-gray-500 mt-1">{{ entry.items?.length || 0 }} {{ t('detail.items') }}</p>
        </div>
        
        <div class="overflow-x-auto">
          <table v-if="entry.items && entry.items.length > 0" class="min-w-full divide-y divide-gray-200/50">
            <thead class="bg-gray-50/50">
              <tr>
                <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('detail.item') }}</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('detail.quantity') }}</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('detail.unitPrice') }}</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('detail.total') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200/50">
              <tr v-for="item in entry.items" :key="item.id" class="hover:bg-white/40 transition-colors">
                <td class="px-6 py-4 text-sm text-gray-900 font-medium">{{ item.name }}</td>
                <td class="px-6 py-4 text-sm text-gray-600 text-right">{{ item.quantity }}</td>
                <td class="px-6 py-4 text-sm text-gray-600 text-right">{{ formatCurrency(item.unit_price || 0, entry.currency) }}</td>
                <td class="px-6 py-4 text-sm text-gray-900 text-right font-bold">{{ formatCurrency(item.line_total || 0, entry.currency) }}</td>
              </tr>
            </tbody>
            <tfoot class="bg-gray-50/50">
              <tr>
                <td colspan="3" class="px-6 py-4 text-sm font-bold text-gray-800 text-right">{{ t('detail.subtotal') }}:</td>
                <td class="px-6 py-4 text-sm font-bold text-gray-900 text-right">{{ formatCurrency(entry.amount || 0, entry.currency) }}</td>
              </tr>
              <tr v-if="entry.tax">
                <td colspan="3" class="px-6 py-4 text-sm font-bold text-gray-800 text-right">{{ t('detail.tax') }}:</td>
                <td class="px-6 py-4 text-sm font-bold text-gray-900 text-right">{{ formatCurrency(entry.tax || 0, entry.currency) }}</td>
              </tr>
              <tr class="border-t-2 border-gray-300">
                <td colspan="3" class="px-6 py-4 text-base font-bold text-gray-800 text-right">{{ t('detail.total') }}:</td>
                <td class="px-6 py-4 text-base font-bold text-gray-900 text-right">{{ formatCurrency(entry.total || 0, entry.currency) }}</td>
              </tr>
            </tfoot>
          </table>
          
          <div v-else class="text-center py-12 text-gray-500">
            <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
            </svg>
            <p class="text-lg font-medium">{{ t('detail.noLineItems') }}</p>
          </div>
        </div>
      </div>

      <!-- Journal Entry (Double-Entry Accounting) -->
      <div class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 overflow-hidden shadow-xl">
        <div class="px-6 py-4 border-b border-gray-200/50 bg-gradient-to-r from-blue-50/50 to-purple-50/50">
          <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"></path>
            </svg>
            {{ t('accounting.journalEntry') }}
          </h3>
          <p class="text-sm text-gray-500 mt-1">{{ t('accounting.doubleEntry') }}</p>
        </div>
        
        <div class="overflow-x-auto">
          <table v-if="entry.journal_entry && entry.journal_entry.lines?.length > 0" class="min-w-full divide-y divide-gray-200/50">
            <thead class="bg-gray-50/50">
              <tr>
                <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('accounting.accountCode') }}</th>
                <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('accounting.accountName') }}</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('accounting.debit') }}</th>
                <th class="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('accounting.credit') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200/50">
              <tr v-for="line in entry.journal_entry.lines" :key="line.id" class="hover:bg-white/40 transition-colors">
                <td class="px-6 py-4 text-sm text-gray-600 font-mono">{{ line.account_code }}</td>
                <td class="px-6 py-4 text-sm text-gray-900 font-medium">{{ line.account_name }}</td>
                <td class="px-6 py-4 text-sm text-right" :class="line.debit > 0 ? 'text-blue-700 font-bold' : 'text-gray-400'">
                  {{ line.debit > 0 ? formatCurrency(line.debit, entry.currency) : '-' }}
                </td>
                <td class="px-6 py-4 text-sm text-right" :class="line.credit > 0 ? 'text-purple-700 font-bold' : 'text-gray-400'">
                  {{ line.credit > 0 ? formatCurrency(line.credit, entry.currency) : '-' }}
                </td>
              </tr>
            </tbody>
            <tfoot class="bg-gray-50/50">
              <tr class="border-t-2 border-gray-300">
                <td colspan="2" class="px-6 py-4 text-sm font-bold text-gray-800 text-right">{{ t('accounting.totalDebits') }} / {{ t('accounting.totalCredits') }}:</td>
                <td class="px-6 py-4 text-sm font-bold text-blue-700 text-right">{{ formatCurrency(entry.journal_entry.total_debits || 0, entry.currency) }}</td>
                <td class="px-6 py-4 text-sm font-bold text-purple-700 text-right">{{ formatCurrency(entry.journal_entry.total_credits || 0, entry.currency) }}</td>
              </tr>
              <tr>
                <td colspan="4" class="px-6 py-2 text-center">
                  <span v-if="entry.journal_entry.is_balanced" 
                    class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-50/50 text-green-700 border border-green-200/50">
                    <span class="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5"></span>
                    {{ t('accounting.balanced') }}
                  </span>
                  <span v-else
                    class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-50/50 text-red-700 border border-red-200/50">
                    <span class="w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5"></span>
                    {{ t('accounting.unbalanced') }}
                  </span>
                </td>
              </tr>
            </tfoot>
          </table>
          
          <div v-else class="text-center py-8 text-gray-500">
            <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"></path>
            </svg>
            <p class="text-sm font-medium">{{ t('accounting.noJournalEntry') }}</p>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div v-if="entry.status === 'pending'" class="flex gap-4">
        <button @click="updateStatus('validated')"
          class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-600/20">
          {{ t('detail.validate') }}
        </button>
        <button @click="updateStatus('rejected')"
          class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/20">
          {{ t('detail.reject') }}
        </button>
      </div>

      <button @click="confirmDelete"
        class="w-full px-6 py-3 rounded-xl font-medium transition-all duration-200 bg-red-100 hover:bg-red-200 text-red-700 border border-red-200">
        {{ t('detail.delete') }}
      </button>
    </div>

    <!-- Error State -->
    <div v-else class="text-center py-12 text-gray-500">
      <p class="text-lg font-medium">{{ t('detail.notFound') }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import { useI18n } from '../i18n/i18n.js'

const { t } = useI18n()

const props = defineProps({
  recordId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['back', 'updated', 'deleted'])

const entry = ref(null)
const loading = ref(false)
const perspective = ref(null)
const perspectiveLoading = ref(false)

const loadEntry = async () => {
  loading.value = true
  try {
    const response = await api.getLedgerEntry(props.recordId)
    entry.value = response.data
    
    // DEBUG: Log the response
    console.log('API Response:', response.data)
    console.log('Items array:', response.data.items)
    console.log('Items count:', response.data.items?.length || 0)

    // Load perspective-aware counterparty analysis (best-effort)
    perspectiveLoading.value = true
    try {
      const pResp = await api.getLedgerPerspective(props.recordId)
      perspective.value = pResp.data
    } catch (err) {
      console.warn('Perspective analysis not available:', err)
      perspective.value = null
    } finally {
      perspectiveLoading.value = false
    }
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

const formatCurrency = (amount, currency = 'USD') => {
  const symbols = {
    'USD': '$',
    'IDR': 'Rp',
    'ZAR': 'R',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CNY': '¥',
    'INR': '₹',
    'KRW': '₩'
  }
  
  const symbol = symbols[currency] || (currency + ' ')
  const value = amount || 0
  
  // No decimals for IDR, ZAR, JPY, KRW (whole number currencies)
  if (['IDR', 'ZAR', 'JPY', 'KRW'].includes(currency)) {
    return `${symbol}${value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
  }
  
  return `${symbol}${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

onMounted(() => {
  loadEntry()
})
</script>
