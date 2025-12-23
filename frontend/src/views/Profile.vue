<template>
  <div class="min-h-screen bg-[#F3F4F6] font-sans flex overflow-hidden">
    <!-- Sidebar Navigation (Reuse Dashboard sidebar structure) -->
    <aside 
      class="fixed inset-y-0 left-0 z-50 my-0 lg:my-4 ml-0 lg:ml-4 h-screen lg:h-[calc(100vh-2rem)] w-72 bg-white/80 backdrop-blur-xl border border-white/40 shadow-2xl rounded-none lg:rounded-[2rem] flex flex-col"
    >
      <!-- Logo -->
      <div class="p-6 lg:p-8 flex items-center gap-4">
        <div class="w-10 h-10 lg:w-12 lg:h-12 bg-gradient-to-br from-gray-800 to-black rounded-2xl flex items-center justify-center shadow-lg shadow-gray-900/20">
          <span class="text-white font-bold text-xl lg:text-2xl">A</span>
        </div>
        <div>
          <h1 class="text-lg lg:text-xl font-bold text-gray-800 tracking-tight">Accounting</h1>
          <p class="text-xs text-gray-500 font-medium uppercase tracking-wider">Automation</p>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-4 space-y-2 mt-2">
        <router-link
          to="/"
          class="w-full flex items-center gap-4 px-6 py-4 rounded-2xl transition-all duration-300 text-gray-500 hover:bg-white hover:text-gray-900 hover:shadow-lg hover:shadow-gray-200/50"
        >
          <span class="text-xl">🏠</span>
          <span class="font-semibold">Dashboard</span>
        </router-link>
        <div
          class="w-full flex items-center gap-4 px-6 py-4 rounded-2xl bg-gray-900 text-white shadow-xl shadow-gray-900/20 scale-[1.02]"
        >
          <span class="text-xl">👤</span>
          <span class="font-semibold">Profile</span>
        </div>
      </nav>

      <!-- Logout Button -->
      <div class="p-4">
        <button
          @click="handleLogout"
          class="w-full flex items-center gap-4 px-6 py-4 rounded-2xl bg-red-50 hover:bg-red-100 text-red-600 hover:text-red-700 transition-all duration-300 shadow-lg hover:shadow-xl"
        >
          <span class="text-xl">🚪</span>
          <span class="font-semibold">Logout</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 lg:ml-80 p-2 lg:p-4 min-h-screen relative">
      <div class="bg-white/60 backdrop-blur-xl border border-white/40 shadow-2xl rounded-2xl lg:rounded-[2.5rem] min-h-[calc(100vh-1rem)] lg:min-h-[calc(100vh-2rem)] p-4 lg:p-8 relative overflow-hidden">
        
        <!-- Decorative background blobs -->
        <div class="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none opacity-30">
          <div class="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-200/40 rounded-full blur-[100px] animate-pulse"></div>
          <div class="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-200/40 rounded-full blur-[100px] animate-pulse" style="animation-delay: 2s;"></div>
        </div>

        <!-- Content -->
        <div class="relative z-10">
          <!-- Header -->
          <div class="mb-8">
            <h1 class="text-3xl lg:text-4xl font-bold text-gray-900 mb-2">User Profile</h1>
            <p class="text-gray-600">Manage your account information</p>
          </div>

          <!-- Loading State -->
          <div v-if="loading" class="flex items-center justify-center py-20">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-2xl p-6 mb-6">
            <p class="text-red-800 font-semibold">{{ error }}</p>
          </div>

          <!-- Profile Content -->
          <div v-else-if="user" class="space-y-6">
            <!-- Profile Card -->
            <div class="bg-white/80 backdrop-blur-md rounded-2xl border border-white/40 shadow-xl p-8">
              <div class="flex items-start gap-6">
                <!-- Avatar -->
                <div class="w-20 h-20 lg:w-24 lg:h-24 bg-gradient-to-br from-gray-800 to-black rounded-2xl flex items-center justify-center shadow-lg">
                  <span class="text-white font-bold text-3xl lg:text-4xl">
                    {{ user.email.charAt(0).toUpperCase() }}
                  </span>
                </div>

                <!-- User Info -->
                <div class="flex-1">
                  <h2 class="text-2xl font-bold text-gray-900 mb-2">{{ user.email }}</h2>
                  <p v-if="user.company_name" class="text-lg text-gray-600 mb-4">{{ user.company_name }}</p>
                  <p v-else class="text-gray-400 italic mb-4">No company name set</p>
                  
                  <!-- Account Details -->
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                    <div class="bg-gray-50 rounded-xl p-4">
                      <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Email</p>
                      <p class="text-gray-900 font-medium">{{ user.email }}</p>
                    </div>
                    <div class="bg-gray-50 rounded-xl p-4">
                      <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Company</p>
                      <p class="text-gray-900 font-medium">{{ user.company_name || 'Not set' }}</p>
                    </div>
                    <div class="bg-gray-50 rounded-xl p-4">
                      <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Account Created</p>
                      <p class="text-gray-900 font-medium">{{ formatDate(user.created_at) }}</p>
                    </div>
                    <div class="bg-gray-50 rounded-xl p-4">
                      <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">User ID</p>
                      <p class="text-gray-900 font-mono text-sm">{{ user.id }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Account Actions -->
            <div class="bg-white/80 backdrop-blur-md rounded-2xl border border-white/40 shadow-xl p-8">
              <h3 class="text-xl font-bold text-gray-900 mb-4">Account Actions</h3>
              <div class="space-y-3">
                <button
                  @click="handleLogout"
                  class="w-full md:w-auto px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-xl font-semibold transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api/client'

const router = useRouter()

const user = ref(null)
const loading = ref(true)
const error = ref('')

const fetchUser = async () => {
  loading.value = true
  error.value = ''
  try {
    const response = await api.getCurrentUser()
    user.value = response.data
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load user information'
    if (err.response?.status === 401) {
      // Token expired or invalid
      handleLogout()
    }
  } finally {
    loading.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  router.push('/login')
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    })
  } catch {
    return dateString
  }
}

onMounted(() => {
  fetchUser()
})
</script>

<style scoped>
/* Additional styles if needed */
</style>

