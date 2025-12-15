import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  // Process receipt (single)
  async processReceipt(file, ocrEngine = 'easyocr', recordId = null, language = 'en') {
    const formData = new FormData()
    formData.append('file', file)
    const params = { ocr_engine: ocrEngine, language }
    if (recordId) {
      params.record_id = recordId
    }
    return client.post('/process-receipt', formData, {
      params: params,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  // Process multiple receipts (batch)
  async processReceiptsBatch(files, ocrEngine = 'easyocr', language = 'en') {
    const formData = new FormData()
    // FastAPI expects multiple files with the same parameter name
    for (const file of files) {
      formData.append('files', file)
    }
    return client.post('/process-receipts-batch', formData, {
      params: { ocr_engine: ocrEngine, language },
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  // Get ledger entries
  async getLedger(skip = 0, limit = 100, status = null, vendor = null) {
    const params = { skip, limit }
    if (status) params.status = status
    if (vendor) params.vendor = vendor
    return client.get('/ledger', { params })
  },

  // Get single ledger entry
  async getLedgerEntry(recordId) {
    return client.get(`/ledger/${recordId}`)
  },

  // Get perspective-aware counterparty analysis for a ledger entry
  async getLedgerPerspective(recordId, ourCompanyName = null) {
    const params = {}
    if (ourCompanyName) {
      params.our_company_name = ourCompanyName
    }
    return client.get(`/ledger/${recordId}/perspective`, { params })
  },

  // Approve ledger entry
  async approveLedgerEntry(recordId) {
    return client.post(`/ledger/${recordId}/approve`)
  },

  // Update ledger entry status
  async updateLedgerEntryStatus(recordId, status) {
    return client.put(`/ledger/${recordId}/status`, null, {
      params: { status }
    })
  },

  // Delete ledger entry
  async deleteLedgerEntry(recordId) {
    return client.delete(`/ledger/${recordId}`)
  },

  // Chat with ledger
  async chat(message, recordId = null, model = null) {
    return client.post('/chat', { 
      message, 
      record_id: recordId,
      model: model
    })
  },

  // Get stats
  async getStats() {
    return client.get('/stats')
  },

  // Convert currency
  async convertCurrency(amount, fromCurrency, toCurrency = 'USD') {
    return client.post('/convert-currency', null, {
      params: {
        amount,
        from_currency: fromCurrency,
        to_currency: toCurrency
      }
    })
  },

  // Create manual ledger entry
  async createManualEntry(entryData) {
    return client.post('/ledger/manual', entryData)
  },
}

export default client

