<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
    <h2 class="text-2xl font-bold text-gray-900 mb-6">Chat with Ledger</h2>
    
    <!-- Chat Messages -->
    <div class="space-y-4 mb-6 h-96 overflow-y-auto border border-gray-200 rounded-lg p-4 bg-gray-50">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="[
          'flex',
          message.role === 'user' ? 'justify-end' : 'justify-start'
        ]"
      >
        <div
          :class="[
            'max-w-3xl rounded-lg px-4 py-2',
            message.role === 'user'
              ? 'bg-primary-600 text-white'
              : 'bg-white text-gray-900 border border-gray-200'
          ]"
        >
          <p class="text-sm whitespace-pre-wrap">{{ message.content }}</p>
          <div v-if="message.sources?.length" class="mt-2 pt-2 border-t border-gray-200">
            <p class="text-xs font-medium text-gray-500 mb-1">Sources:</p>
            <ul class="text-xs space-y-1">
              <li v-for="(source, i) in message.sources" :key="i" class="text-gray-600">
                • {{ source.vendor }} ({{ (source.similarity * 100).toFixed(1) }}% match)
              </li>
            </ul>
          </div>
        </div>
      </div>
      
      <div v-if="loading" class="flex justify-start">
        <div class="bg-white border border-gray-200 rounded-lg px-4 py-2">
          <div class="flex space-x-2">
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Chat Input -->
    <form @submit.prevent="sendMessage" class="flex space-x-4">
      <input
        v-model="inputMessage"
        type="text"
        placeholder="Ask about receipts, invoices, or ledger entries..."
        class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all flex-1"
        :disabled="loading"
      />
      <button
        type="submit"
        :disabled="loading || !inputMessage.trim()"
        class="px-4 py-2 rounded-lg font-medium transition-colors duration-200 bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Send
      </button>
    </form>

    <!-- Example Questions -->
    <div class="mt-6">
      <p class="text-sm font-medium text-gray-500 mb-2">Example Questions:</p>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="example in exampleQuestions"
          :key="example"
          @click="inputMessage = example"
          class="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors"
        >
          {{ example }}
        </button>
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
    const response = await api.chat(userMessage)
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

