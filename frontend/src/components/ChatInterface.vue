<template>
  <div class="space-y-8 h-full flex flex-col">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 flex-shrink-0">
      <div>
        <h2 class="text-xl lg:text-2xl font-bold text-gray-800">AI Assistant</h2>
        <p class="text-sm lg:text-base text-gray-500 mt-1">Ask questions about your financial data</p>
      </div>
      
      <!-- Model Selection -->
      <div class="flex items-center gap-2">
        <label class="text-xs font-semibold text-gray-600">Model:</label>
        <select v-model="selectedModel"
          class="px-3 py-2 bg-white/80 border border-white/50 rounded-xl text-sm font-medium focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all min-w-[200px]">
          <option v-for="model in geminiModels" :key="model" :value="model">
            {{ model }}
          </option>
        </select>
      </div>
    </div>

    <!-- Chat Area -->
    <div class="bg-white/40 backdrop-blur-md rounded-3xl border border-white/40 shadow-xl shadow-gray-200/20 flex-1 flex flex-col overflow-hidden relative">
      <!-- Messages -->
      <div class="flex-1 overflow-y-auto p-4 lg:p-6 space-y-4 lg:space-y-6 scroll-smooth">
        <div
          v-for="(message, index) in messages"
          :key="index"
          :class="[
            'flex w-full',
            message.role === 'user' ? 'justify-end' : 'justify-start'
          ]"
        >
          <div
            :class="[
              'max-w-[95%] lg:max-w-[80%] rounded-2xl px-4 lg:px-6 py-3 lg:py-4 shadow-sm',
              message.role === 'user'
                ? 'bg-gray-900 text-white rounded-tr-sm'
                : 'bg-white/80 backdrop-blur-sm text-gray-800 border border-white/50 rounded-tl-sm'
            ]"
          >
            <p class="text-sm leading-relaxed whitespace-pre-wrap">{{ message.content }}</p>
            
            <!-- Sources -->
            <div v-if="message.sources?.length" class="mt-4 pt-4 border-t border-gray-200/20">
              <p class="text-xs font-bold uppercase tracking-wider opacity-70 mb-2">Sources</p>
              <div class="space-y-2">
                <div 
                  v-for="(source, i) in message.sources" 
                  :key="i" 
                  class="bg-black/5 rounded-lg p-2 text-xs flex justify-between items-center"
                >
                  <span class="font-medium truncate max-w-[70%]">{{ source.vendor }}</span>
                  <span class="opacity-70">{{ (source.similarity * 100).toFixed(0) }}% match</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Loading Indicator -->
        <div v-if="loading" class="flex justify-start w-full">
          <div class="bg-white/80 backdrop-blur-sm border border-white/50 rounded-2xl rounded-tl-sm px-6 py-4 shadow-sm">
            <div class="flex space-x-2">
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
              <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="p-4 lg:p-6 bg-white/40 backdrop-blur-md border-t border-white/40">
        <!-- Example Questions -->
        <div v-if="messages.length < 3" class="mb-6 overflow-x-auto pb-2">
          <div class="flex gap-2">
            <button
              v-for="example in exampleQuestions"
              :key="example"
              @click="inputMessage = example"
              class="whitespace-nowrap px-4 py-2 bg-white/60 hover:bg-white border border-white/50 rounded-xl text-xs font-medium text-gray-600 transition-all shadow-sm hover:shadow-md"
            >
              {{ example }}
            </button>
          </div>
        </div>

        <form @submit.prevent="sendMessage" class="relative">
          <input
            v-model="inputMessage"
            type="text"
            placeholder="Ask about receipts, invoices, or ledger entries..."
            class="w-full pl-6 pr-14 py-4 bg-white/80 border border-white/50 rounded-2xl focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 outline-none transition-all shadow-inner placeholder-gray-400"
            :disabled="loading"
          />
          <button
            type="submit"
            :disabled="loading || !inputMessage.trim()"
            class="absolute right-2 top-2 p-2 bg-gray-900 text-white rounded-xl hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-gray-900/20"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api/client'

const messages = ref([
  {
    role: 'assistant',
    content: 'Hello! I can help you query your ledger and receipts. Ask me anything about your transactions, vendors, or amounts.',
    sources: null
  }
])
const inputMessage = ref('')
const loading = ref(false)
const selectedModel = ref('gemini-2.5-flash')

// Available Gemini models
const geminiModels = [
  'gemini-3-pro-preview',
  'gemini-2.5-pro',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
  'gemini-flash-latest',
  'gemini-flash-lite-latest'
]

const exampleQuestions = [
  'What is the total amount spent?',
  'Show me all transactions from last month',
  'Which vendor has the highest total?',
  'Find receipts with tax over $100'
]

const sendMessage = async () => {
  if (!inputMessage.value.trim() || loading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''
  
  messages.value.push({
    role: 'user',
    content: userMessage,
    sources: null
  })

  loading.value = true

  try {
    const response = await api.chat(userMessage, null, selectedModel.value)
    messages.value.push({
      role: 'assistant',
      content: response.data.response,
      sources: response.data.sources
    })
  } catch (error) {
    console.error('Error sending message:', error)
    messages.value.push({
      role: 'assistant',
      content: 'Sorry, I encountered an error. Please try again.',
      sources: null
    })
  } finally {
    loading.value = false
  }
}
</script>

