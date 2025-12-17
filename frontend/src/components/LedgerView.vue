<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h2 class="text-xl lg:text-2xl font-bold text-gray-800">{{ t('ledger.title') }}</h2>
        <p class="text-sm lg:text-base text-gray-500 mt-1">{{ t('ledger.subtitle') }}</p>
      </div>
      <div class="flex gap-2 sm:gap-3">
        <button
          @click="exportToCSV"
          class="px-3 sm:px-4 py-2 bg-white/50 hover:bg-white/80 text-gray-700 rounded-xl text-sm font-medium transition-all duration-200 border border-white/40 shadow-sm backdrop-blur-sm">
          <span class="hidden sm:inline">{{ t('ledger.exportCsv') }}</span>
          <span class="sm:hidden">📊</span>
        </button>
        <button
          @click="showManualEntryModal = true"
          class="px-3 sm:px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-xl text-sm font-medium transition-all duration-200 shadow-lg shadow-gray-900/20">
          <span class="hidden sm:inline">{{ t('ledger.addManual') }}</span>
          <span class="sm:hidden">+</span>
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-6">
      <div
        class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-4 lg:p-6 shadow-lg shadow-gray-200/20 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-gray-500 uppercase tracking-wider">{{ t('ledger.total') }}</div>
        <div class="text-2xl lg:text-3xl font-bold text-gray-800 mt-2">{{ stats.total_entries || 0 }}</div>
      </div>
      <div
        class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-4 lg:p-6 shadow-lg shadow-gray-200/20 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-gray-500 uppercase tracking-wider">{{ t('ledger.amount') }}</div>
        <div class="text-2xl lg:text-3xl font-bold text-gray-800 mt-2">${{ (stats.total_amount || 0).toFixed(2) }}</div>
        <div class="text-xs text-gray-400 mt-1">{{ t('ledger.usdConverted') }}</div>
      </div>
      <div
        class="bg-green-50/40 backdrop-blur-md rounded-2xl border border-green-100/40 p-4 lg:p-6 shadow-lg shadow-green-900/5 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-green-600 uppercase tracking-wider">{{ t('ledger.validated') }}</div>
        <div class="text-2xl lg:text-3xl font-bold text-green-700 mt-2">{{ stats.validated_entries || 0 }}</div>
      </div>
      <div
        class="bg-yellow-50/40 backdrop-blur-md rounded-2xl border border-yellow-100/40 p-4 lg:p-6 shadow-lg shadow-yellow-900/5 hover:scale-[1.02] transition-transform duration-300">
        <div class="text-xs lg:text-sm font-medium text-yellow-600 uppercase tracking-wider">{{ t('ledger.pending') }}</div>
        <div class="text-2xl lg:text-3xl font-bold text-yellow-700 mt-2">{{ stats.pending_entries || 0 }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div
      class="bg-white/40 backdrop-blur-md rounded-2xl border border-white/40 p-4 lg:p-6 shadow-lg shadow-gray-200/20">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-6">
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{{ t('ledger.status') }}</label>
          <div class="relative">
            <select v-model="filters.status" @change="loadLedger"
              class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all appearance-none cursor-pointer">
              <option value="">{{ t('ledger.allStatuses') }}</option>
              <option value="validated">{{ t('ledger.validated') }}</option>
              <option value="pending">{{ t('ledger.pending') }}</option>
              <option value="rejected">{{ t('ledger.rejected') }}</option>
            </select>
            <div class="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none text-gray-500">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
              </svg>
            </div>
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{{ t('ledger.vendor') }}</label>
          <div class="relative">
            <input v-model="filters.vendor" @input="debounceLoadLedger" type="text" :placeholder="t('ledger.searchVendor')"
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
            {{ t('ledger.clearFilters') }}
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
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('ledger.date') }}</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('ledger.vendor') }}</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('ledger.amount') }}</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('ledger.total') }}</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('ledger.status') }}</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('ledger.confidence') }}
              </th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Reconciliation</th>
              <th class="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">{{ t('ledger.actions') }}</th>
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
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{{ formatCurrencyUSD(entry.usd_amount || entry.amount, entry.currency) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">{{ formatCurrencyUSD(entry.usd_total || entry.total, entry.currency) }}</td>
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
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <div class="flex items-center gap-2">
                    <span
                      v-if="entry.reconciliation_status === 'reconciled'"
                      class="px-2 py-1 bg-green-100 text-green-700 rounded-lg text-xs font-medium"
                      title="Reconciled transaction"
                    >
                      ✓ Reconciled
                    </span>
                    <span
                      v-else-if="entry.reconciliation_status === 'counterparty'"
                      class="px-2 py-1 bg-blue-100 text-blue-700 rounded-lg text-xs font-medium"
                      title="Counterparty document"
                    >
                      🔗 Counterparty
                    </span>
                    <span
                      v-else
                      class="px-2 py-1 bg-gray-100 text-gray-600 rounded-lg text-xs font-medium"
                      title="Not reconciled"
                    >
                      —
                    </span>
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
              <td colspan="9" class="px-6 py-12 text-center">
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
                <p class="text-2xl font-bold text-gray-900 mt-1">{{ formatCurrencyUSD(selectedEntry.usd_total || selectedEntry.total || 0, selectedEntry.currency) }}</p>
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
                      <td class="px-5 py-3 text-sm text-gray-600 text-right">{{ formatCurrencyUSD(item.unit_price || 0, selectedEntry.currency) }}
                      </td>
                      <td class="px-5 py-3 text-sm text-gray-900 text-right font-bold">{{ formatCurrencyUSD(item.line_total || 0, selectedEntry.currency) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Reconciliation Info -->
            <div v-if="selectedEntry.reconciliation" class="bg-blue-50/50 rounded-2xl p-5 border border-blue-100">
              <label class="text-xs font-bold text-blue-600 uppercase tracking-wider block mb-2">Reconciliation Status</label>
              <div v-if="selectedEntry.reconciliation.is_counterparty" class="space-y-2">
                <p class="text-sm text-blue-800 font-semibold">Counterparty Document</p>
                <p v-if="selectedEntry.reconciliation.counterparty_record_id" class="text-sm text-blue-700">
                  Related Transaction: <span class="font-mono">{{ selectedEntry.reconciliation.counterparty_record_id }}</span>
                </p>
                <p v-if="selectedEntry.reconciliation.counterparty_vendor" class="text-sm text-blue-700">
                  Counterparty Vendor: {{ selectedEntry.reconciliation.counterparty_vendor }}
                </p>
              </div>
              <div v-else-if="selectedEntry.reconciliation.is_duplicate" class="space-y-2">
                <p class="text-sm text-red-800 font-semibold">Duplicate Document</p>
                <p v-if="selectedEntry.reconciliation.duplicate_record_id" class="text-sm text-red-700">
                  Duplicate of: <span class="font-mono">{{ selectedEntry.reconciliation.duplicate_record_id }}</span>
                </p>
              </div>
              <div v-else-if="selectedEntry.reconciliation.reconciled" class="space-y-2">
                <p class="text-sm text-green-800 font-semibold">✓ Reconciled</p>
                <p v-if="selectedEntry.reconciliation.total_matches > 0" class="text-sm text-green-700">
                  {{ selectedEntry.reconciliation.total_matches }} matching transaction(s) found
                </p>
              </div>
              <div v-else class="text-sm text-gray-600">
                No reconciliation matches found
              </div>
            </div>

            <!-- Reconciliation Info -->
            <div v-if="selectedEntry.reconciliation" class="bg-blue-50/50 rounded-2xl p-5 border border-blue-100">
              <label class="text-xs font-bold text-blue-600 uppercase tracking-wider block mb-2">Reconciliation Status</label>
              <div v-if="selectedEntry.reconciliation.is_counterparty" class="space-y-2">
                <p class="text-sm text-blue-800 font-semibold">Counterparty Document</p>
                <p v-if="selectedEntry.reconciliation.counterparty_record_id" class="text-sm text-blue-700">
                  Related Transaction: <span class="font-mono">{{ selectedEntry.reconciliation.counterparty_record_id }}</span>
                </p>
                <p v-if="selectedEntry.reconciliation.counterparty_vendor" class="text-sm text-blue-700">
                  Counterparty Vendor: {{ selectedEntry.reconciliation.counterparty_vendor }}
                </p>
              </div>
              <div v-else-if="selectedEntry.reconciliation.is_duplicate" class="space-y-2">
                <p class="text-sm text-red-800 font-semibold">Duplicate Document</p>
                <p v-if="selectedEntry.reconciliation.duplicate_record_id" class="text-sm text-red-700">
                  Duplicate of: <span class="font-mono">{{ selectedEntry.reconciliation.duplicate_record_id }}</span>
                </p>
              </div>
              <div v-else-if="selectedEntry.reconciliation.reconciled" class="space-y-2">
                <p class="text-sm text-green-800 font-semibold">✓ Reconciled</p>
                <p v-if="selectedEntry.reconciliation.total_matches > 0" class="text-sm text-green-700">
                  {{ selectedEntry.reconciliation.total_matches }} matching transaction(s) found
                </p>
              </div>
              <div v-else class="text-sm text-gray-600">
                No reconciliation matches found
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

    <!-- Manual Entry Modal -->
    <div v-if="showManualEntryModal"
      class="fixed inset-0 bg-gray-900/40 backdrop-blur-sm flex items-center justify-center z-[60] p-4 transition-all duration-300 overflow-y-auto"
      @click.self="showManualEntryModal = false">
      <div
        class="bg-white/90 backdrop-blur-xl rounded-2xl lg:rounded-3xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-white/50 my-4">
        <div class="p-8">
          <div class="flex justify-between items-start mb-8">
            <div>
              <h3 class="text-2xl font-bold text-gray-900">Add Manual Transaction</h3>
              <p class="text-gray-500 text-sm mt-1">Enter transaction details manually</p>
            </div>
            <button @click="showManualEntryModal = false"
              class="p-2 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors">
              <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="submitManualEntry" class="space-y-6">
            <!-- Basic Information -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Vendor *</label>
                <input v-model="manualEntry.vendor" type="text" required
                  class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all"
                  placeholder="Vendor name" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Date *</label>
                <input v-model="manualEntry.date" type="date" required
                  class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all" />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Currency *</label>
                <select v-model="manualEntry.currency" required
                  class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all">
                  <option value="USD">USD ($)</option>
                  <option value="IDR">IDR (Rp)</option>
                  <option value="ZAR">ZAR (R)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Amount</label>
                <input v-model.number="manualEntry.amount" type="number" step="0.01" min="0"
                  class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all"
                  placeholder="0.00" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Tax</label>
                <input v-model.number="manualEntry.tax" type="number" step="0.01" min="0"
                  class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all"
                  placeholder="0.00" />
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Total *</label>
              <input v-model.number="manualEntry.total" type="number" step="0.01" min="0" required
                class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all"
                placeholder="0.00" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Category</label>
                <input v-model="manualEntry.category" type="text"
                  class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all"
                  placeholder="e.g., Office Supplies" />
              </div>
              <div>
                <label class="block text-sm font-semibold text-gray-700 mb-2">Payment Method</label>
                <select v-model="manualEntry.payment_method"
                  class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all">
                  <option value="">Select...</option>
                  <option value="CASH">Cash</option>
                  <option value="CARD">Card</option>
                  <option value="CHECK">Check</option>
                  <option value="TRANSFER">Transfer</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Invoice Number</label>
              <input v-model="manualEntry.invoice_number" type="text"
                class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all"
                placeholder="Optional" />
            </div>

            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-2">Description</label>
              <textarea v-model="manualEntry.description" rows="3"
                class="w-full px-4 py-3 bg-white/50 border border-white/40 rounded-xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all"
                placeholder="Transaction description"></textarea>
            </div>

            <!-- Line Items Section -->
            <div>
              <div class="flex justify-between items-center mb-4">
                <label class="block text-sm font-semibold text-gray-700">Line Items</label>
                <button type="button" @click="addLineItem"
                  class="px-4 py-2 bg-gray-900 hover:bg-gray-800 text-white rounded-xl text-sm font-medium transition-all">
                  + Add Item
                </button>
              </div>
              <div v-if="manualEntry.items.length > 0" class="space-y-3">
                <div v-for="(item, index) in manualEntry.items" :key="index"
                  class="bg-white/50 rounded-xl p-4 border border-white/50">
                  <div class="grid grid-cols-12 gap-3 items-end">
                    <div class="col-span-5">
                      <label class="block text-xs font-medium text-gray-600 mb-1">Item Name</label>
                      <input v-model="item.name" type="text" required
                        class="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none"
                        placeholder="Item name" />
                    </div>
                    <div class="col-span-2">
                      <label class="block text-xs font-medium text-gray-600 mb-1">Qty</label>
                      <input v-model.number="item.quantity" type="number" min="1" step="1" required
                        class="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none"
                        placeholder="1" />
                    </div>
                    <div class="col-span-2">
                      <label class="block text-xs font-medium text-gray-600 mb-1">Unit Price</label>
                      <input v-model.number="item.unit_price" type="number" step="0.01" min="0" required
                        class="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none"
                        placeholder="0.00" />
                    </div>
                    <div class="col-span-2">
                      <label class="block text-xs font-medium text-gray-600 mb-1">Total</label>
                      <input :value="((item.quantity || 0) * (item.unit_price || 0)).toFixed(2)" type="text" readonly
                        class="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-600"
                        placeholder="0.00" />
                    </div>
                    <div class="col-span-1">
                      <button type="button" @click="removeLineItem(index)"
                        class="w-full px-3 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-all">
                        ×
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <p v-else class="text-sm text-gray-500 text-center py-4">No line items. Click "Add Item" to add line items.</p>
            </div>

            <!-- Actions -->
            <div class="flex gap-4 pt-6 border-t border-gray-200/50">
              <button type="button" @click="showManualEntryModal = false"
                class="flex-1 px-6 py-3 rounded-xl font-medium transition-all duration-200 bg-gray-100 hover:bg-gray-200 text-gray-700">
                Cancel
              </button>
              <button type="submit" :disabled="loading"
                class="flex-1 px-6 py-3 rounded-xl font-bold transition-all duration-200 bg-gray-900 hover:bg-gray-800 text-white shadow-lg shadow-gray-900/20 disabled:opacity-50 disabled:cursor-not-allowed">
                {{ loading ? 'Creating...' : 'Create Transaction' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import { useI18n } from '../i18n/i18n.js'

const { t } = useI18n()

const ledgerEntries = ref([])
const stats = ref({})
const selectedEntry = ref(null)
const entryToDelete = ref(null)
const showManualEntryModal = ref(false)
const filters = ref({
  status: '',
  vendor: ''
})
const loading = ref(false)
const conversionCache = ref({}) // Cache for currency conversions: { "IDR:1000": 0.067 }
const manualEntry = ref({
  vendor: '',
  date: new Date().toISOString().split('T')[0],
  amount: null,
  tax: null,
  total: null,
  currency: 'USD',
  category: '',
  payment_method: '',
  invoice_number: '',
  description: '',
  items: []
})

let debounceTimer = null

const loadLedger = async () => {
  try {
    const response = await api.getLedger(0, 100, filters.value.status || null, filters.value.vendor || null)
    ledgerEntries.value = response.data
    
    // Convert all non-USD amounts to USD
    await convertAllToUSD()
  } catch (error) {
    console.error('Error loading ledger:', error)
  }
}

const convertAllToUSD = async () => {
  // Group entries by currency to minimize API calls
  const conversionPromises = []
  
  for (const entry of ledgerEntries.value) {
    const currency = entry.currency || 'USD'
    if (currency !== 'USD') {
      // Use stored usd_total from backend if available
      if (entry.usd_total) {
        entry.usd_total = entry.usd_total
      } else if (entry.total) {
        // Only convert if usd_total is not available
        conversionPromises.push(convertToUSD(entry, 'total'))
      }
      
      // For amount field, calculate from usd_total if available, otherwise convert
      if (entry.usd_total && entry.total && entry.amount) {
        // Calculate usd_amount proportionally
        entry.usd_amount = (entry.usd_total / entry.total) * entry.amount
      } else if (entry.amount) {
        conversionPromises.push(convertToUSD(entry, 'amount'))
      }
    } else {
      // Already USD, use existing values
      entry.usd_amount = entry.amount
      entry.usd_total = entry.usd_total || entry.total
    }
  }
  
  // Wait for all conversions to complete
  await Promise.all(conversionPromises)
}

const convertToUSD = async (entry, field) => {
  const currency = entry.currency || 'USD'
  const amount = entry[field]
  
  if (!amount || currency === 'USD') {
    if (field === 'amount') {
      entry.usd_amount = amount
    } else if (field === 'total') {
      entry.usd_total = amount
    }
    return
  }
  
  // Check cache first
  const cacheKey = `${currency}:${amount}`
  if (conversionCache.value[cacheKey]) {
    if (field === 'amount') {
      entry.usd_amount = conversionCache.value[cacheKey]
    } else if (field === 'total') {
      entry.usd_total = conversionCache.value[cacheKey]
    }
    return
  }
  
  try {
    // Use stored usd_total if available (from backend)
    if (field === 'total' && entry.usd_total) {
      conversionCache.value[cacheKey] = entry.usd_total
      return
    }
    
    // Call conversion API
    const response = await api.convertCurrency(amount, currency, 'USD')
    const convertedAmount = response.data.converted_amount
    if (field === 'amount') {
      entry.usd_amount = convertedAmount
    } else if (field === 'total') {
      entry.usd_total = convertedAmount
    }
    conversionCache.value[cacheKey] = convertedAmount
  } catch (error) {
    console.error(`Error converting ${field} for entry ${entry.record_id}:`, error)
    // Fallback: use stored usd_total or original amount
    if (field === 'total' && entry.usd_total) {
      conversionCache.value[cacheKey] = entry.usd_total
    } else {
      const fallback = field === 'total' && entry.usd_total ? entry.usd_total : amount
      if (field === 'amount') {
        entry.usd_amount = fallback
      } else if (field === 'total') {
        entry.usd_total = fallback
      }
    }
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
    
    // Convert to USD if needed
    const currency = selectedEntry.value.currency || 'USD'
    if (currency !== 'USD') {
      if (selectedEntry.value.total && !selectedEntry.value.usd_total) {
        await convertToUSD(selectedEntry.value, 'total')
      }
    } else {
      selectedEntry.value.usd_total = selectedEntry.value.usd_total || selectedEntry.value.total
    }
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

// Format currency for LedgerView - always display in USD
const formatCurrencyUSD = (amount, originalCurrency = 'USD') => {
  const value = amount || 0
  // Always show USD in ledger view (amounts are already converted)
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// Keep original formatCurrency for other uses if needed
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

const addLineItem = () => {
  manualEntry.value.items.push({
    name: '',
    quantity: 1,
    unit_price: 0,
    line_total: 0
  })
}

const removeLineItem = (index) => {
  manualEntry.value.items.splice(index, 1)
}

const submitManualEntry = async () => {
  if (loading.value) return
  loading.value = true
  
  try {
    // Prepare entry data
    const entryData = { ...manualEntry.value }
    
    // Calculate totals from items if items exist
    if (entryData.items.length > 0) {
      entryData.items = entryData.items.map(item => ({
        name: item.name,
        quantity: item.quantity || 1,
        unit_price: item.unit_price || 0,
        line_total: (item.quantity || 1) * (item.unit_price || 0)
      }))
      
      const itemsTotal = entryData.items.reduce((sum, item) => sum + item.line_total, 0)
      
      if (!entryData.amount) {
        entryData.amount = itemsTotal
      }
      if (!entryData.total) {
        entryData.total = itemsTotal + (entryData.tax || 0)
      }
    } else {
      // No items, ensure amount is set
      if (!entryData.amount) {
        entryData.amount = entryData.total - (entryData.tax || 0)
      }
    }
    
    await api.createManualEntry(entryData)
    
    // Reset form
    manualEntry.value = {
      vendor: '',
      date: new Date().toISOString().split('T')[0],
      amount: null,
      tax: null,
      total: null,
      currency: 'USD',
      category: '',
      payment_method: '',
      invoice_number: '',
      description: '',
      items: []
    }
    
    showManualEntryModal.value = false
    
    // Reload ledger and stats
    await loadLedger()
    await loadStats()
  } catch (error) {
    console.error('Error creating manual entry:', error)
    alert('Failed to create transaction: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const exportToCSV = () => {
  // Prepare CSV data
  const headers = [
    'Record ID',
    'Date',
    'Vendor',
    'Amount (Original Currency)',
    'Total (Original Currency)',
    'Currency',
    'Amount (USD)',
    'Total (USD)',
    'Tax',
    'Status',
    'Category',
    'Payment Method',
    'Invoice Number',
    'Description',
    'Validation Confidence',
    'Created At'
  ]
  
  const rows = ledgerEntries.value.map(entry => [
    entry.record_id || '',
    entry.date || '',
    entry.vendor || '',
    entry.amount || 0,
    entry.total || 0,
    entry.currency || 'USD',
    entry.usd_amount || entry.amount || 0,
    entry.usd_total || entry.total || 0,
    entry.tax || 0,
    entry.status || '',
    entry.category || '',
    entry.payment_method || '',
    entry.invoice_number || '',
    entry.description || '',
    entry.validation_confidence ? (entry.validation_confidence * 100).toFixed(2) + '%' : '',
    entry.created_at || ''
  ])
  
  // Convert to CSV format
  const escapeCSV = (value) => {
    if (value === null || value === undefined) return ''
    const stringValue = String(value)
    // If contains comma, quote, or newline, wrap in quotes and escape quotes
    if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
      return `"${stringValue.replace(/"/g, '""')}"`
    }
    return stringValue
  }
  
  const csvContent = [
    headers.map(escapeCSV).join(','),
    ...rows.map(row => row.map(escapeCSV).join(','))
  ].join('\n')
  
  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `ledger_export_${new Date().toISOString().split('T')[0]}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

onMounted(() => {
  loadLedger()
  loadStats()
})
</script>
