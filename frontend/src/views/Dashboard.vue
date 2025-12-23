<template>
  <div class="min-h-screen bg-[#F3F4F6] font-sans flex overflow-hidden">
    <!-- Mobile Menu Overlay -->
    <div 
      v-if="mobileMenuOpen" 
      class="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-40 lg:hidden"
      @click="mobileMenuOpen = false"
    ></div>

    <!-- Language Toggle Button (Top Right) -->
    <button 
      @click="toggleLocale"
      class="fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-2 bg-white/80 backdrop-blur-xl border border-white/40 shadow-xl rounded-2xl transition-all duration-300 hover:scale-105 hover:shadow-2xl"
    >
      <span class="text-lg">{{ locale === 'en' ? '🇺🇸' : '🇯🇵' }}</span>
      <span class="text-sm font-medium text-gray-700">{{ locale === 'en' ? 'EN' : 'JA' }}</span>
    </button>

    <!-- Sidebar -->
    <aside 
      :class="[
        'fixed inset-y-0 left-0 z-50 my-0 lg:my-4 ml-0 lg:ml-4 h-screen lg:h-[calc(100vh-2rem)] w-72 bg-white/80 backdrop-blur-xl border border-white/40 shadow-2xl rounded-none lg:rounded-[2rem] flex flex-col transition-all duration-300',
        mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
      ]"
    >
      <!-- Logo -->
      <div class="p-6 lg:p-8 flex items-center gap-4">
        <div class="w-10 h-10 lg:w-12 lg:h-12 bg-gradient-to-br from-gray-800 to-black rounded-2xl flex items-center justify-center shadow-lg shadow-gray-900/20">
          <span class="text-white font-bold text-xl lg:text-2xl">A</span>
        </div>
        <div>
          <h1 class="text-lg lg:text-xl font-bold text-gray-800 tracking-tight">{{ t('nav.accounting') }}</h1>
          <p class="text-xs text-gray-500 font-medium uppercase tracking-wider">{{ t('nav.automation') }}</p>
        </div>
        <!-- Close button for mobile -->
        <button 
          @click="mobileMenuOpen = false"
          class="ml-auto lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-4 space-y-2 mt-2">
        <button
          v-for="tab in translatedTabs"
          :key="tab.id"
          @click="handleTabChange(tab.id); mobileMenuOpen = false"
          :class="[
            'w-full flex items-center gap-4 px-6 py-4 rounded-2xl transition-all duration-300 group relative overflow-hidden',
            activeTab === tab.id
              ? 'bg-gray-900 text-white shadow-xl shadow-gray-900/20 scale-[1.02]'
              : 'text-gray-500 hover:bg-white hover:text-gray-900 hover:shadow-lg hover:shadow-gray-200/50'
          ]"
        >
          <span class="text-xl relative z-10">{{ tab.icon }}</span>
          <span class="font-semibold relative z-10">{{ tab.name }}</span>
          
          <!-- Hover effect background -->
          <div v-if="activeTab !== tab.id" class="absolute inset-0 bg-gradient-to-r from-white to-gray-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        </button>
        
        <!-- Profile Link -->
        <router-link
          to="/profile"
          @click="mobileMenuOpen = false"
          class="w-full flex items-center gap-4 px-6 py-4 rounded-2xl transition-all duration-300 text-gray-500 hover:bg-white hover:text-gray-900 hover:shadow-lg hover:shadow-gray-200/50"
        >
          <span class="text-xl">👤</span>
          <span class="font-semibold">{{ t('nav.profile') || 'Profile' }}</span>
        </router-link>
      </nav>

    
    </aside>

    <!-- Main Content -->
    <main class="flex-1 lg:ml-80 p-2 lg:p-4 min-h-screen relative">
       <!-- Mobile Menu Button -->
       <button
         @click="mobileMenuOpen = true"
         class="lg:hidden fixed top-4 left-4 z-30 p-3 bg-white/80 backdrop-blur-xl border border-white/40 shadow-2xl rounded-2xl transition-all duration-300 hover:scale-105"
       >
         <svg class="w-6 h-6 text-gray-800" fill="none" stroke="currentColor" viewBox="0 0 24 24">
           <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
         </svg>
       </button>

       <!-- Main Glass Container -->
       <div class="bg-white/60 backdrop-blur-xl border border-white/40 shadow-2xl rounded-2xl lg:rounded-[2.5rem] min-h-[calc(100vh-1rem)] lg:min-h-[calc(100vh-2rem)] p-4 lg:p-8 relative overflow-hidden">
          
          <!-- Decorative background blobs -->
          <div class="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none opacity-30">
              <div class="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-200/40 rounded-full blur-[100px] animate-pulse"></div>
              <div class="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-200/40 rounded-full blur-[100px] animate-pulse" style="animation-delay: 2s;"></div>
              <div class="absolute top-[40%] left-[40%] w-[30%] h-[30%] bg-pink-200/30 rounded-full blur-[80px] animate-pulse" style="animation-delay: 4s;"></div>
          </div>

          <!-- Content Transition -->
          <transition name="fade" mode="out-in">
            <div :key="activeTab + (selectedTransaction || '') + locale" class="h-full relative z-10">
               <UploadReceipt v-if="activeTab === 'upload'" @receipt-processed="handleReceiptProcessed" />
               
               <TransactionDetail 
                 v-if="activeTab === 'ledger' && selectedTransaction"
                 :recordId="selectedTransaction"
                 @back="() => { selectedTransaction = null; handleTabChange('ledger') }"
                 @updated="handleTransactionUpdated"
                 @deleted="handleTransactionDeleted"
               />
               
               <LedgerView 
                 v-else-if="activeTab === 'ledger'"
                 @select-transaction="selectTransaction"
               />
               
               <ClaimRightsView v-if="activeTab === 'claim-rights'" />
               
               <ChatInterface v-if="activeTab === 'chat'" />
            </div>
          </transition>
       </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import UploadReceipt from '../components/UploadReceipt.vue'
import LedgerView from '../components/LedgerView.vue'
import TransactionDetail from '../components/TransactionDetail.vue'
import ChatInterface from '../components/ChatInterface.vue'
import ClaimRightsView from '../components/ClaimRightsView.vue'
import { useI18n } from '../i18n/i18n.js'

const { locale, t, toggleLocale } = useI18n()
const router = useRouter()
const route = useRoute()

const activeTab = ref('upload')
const mobileMenuOpen = ref(false)
const selectedTransaction = ref(null)

// Tabs with translated names
const translatedTabs = computed(() => [
  { id: 'upload', name: t('nav.uploadReceipt'), icon: '📤' },
  { id: 'ledger', name: t('nav.transactions'), icon: '📊' },
  { id: 'claim-rights', name: 'Claim Rights', icon: '📋' },
  { id: 'chat', name: t('nav.aiAssistant'), icon: '✨' },
])

// Check authentication on mount
onMounted(() => {
  const token = localStorage.getItem('auth_token')
  if (!token) {
    router.push('/login')
    return
  }
  
  // Handle route query params for tab navigation
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  if (route.query.transaction) {
    selectedTransaction.value = route.query.transaction
  }
})

// Watch for tab changes and update route
const handleTabChange = (tab) => {
  activeTab.value = tab
  selectedTransaction.value = null
  router.push({ query: { tab } })
}

const handleReceiptProcessed = (data) => {
  activeTab.value = 'ledger'
  router.push({ query: { tab: 'ledger' } })
}

const selectTransaction = (recordId) => {
  selectedTransaction.value = recordId
  router.push({ query: { tab: 'ledger', transaction: recordId } })
}

const handleTransactionUpdated = () => {
  // Transaction status was updated, could refresh ledger
}

const handleTransactionDeleted = () => {
  selectedTransaction.value = null
  router.push({ query: { tab: 'ledger' } })
}
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.3);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.5);
}
</style>

