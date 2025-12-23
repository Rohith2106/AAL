import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const client = axios.create({
  baseURL: API_BASE_URL,
})

// Add request interceptor to include auth token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      // Ensure headers object exists and merge Authorization header
      if (!config.headers) {
        config.headers = {}
      }
      // Set Authorization header with Bearer token
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Add response interceptor to handle auth errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      // Only redirect if we're not already on login/signup page
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/signup')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const api = {
  // Process receipt (single)
  async processReceipt(file, ocrEngine = 'easyocr', recordId = null, language = 'en') {
    const formData = new FormData()
    formData.append('file', file)
    const params = { ocr_engine: ocrEngine, language }
    if (recordId) {
      params.record_id = recordId
    }
    // Don't set Content-Type for FormData - axios will set it automatically with boundary
    return client.post('/process-receipt', formData, {
      params: params,
    })
  },

  // Process multiple receipts (batch)
  async processReceiptsBatch(files, ocrEngine = 'easyocr', language = 'en') {
    const formData = new FormData()
    // FastAPI expects multiple files with the same parameter name
    for (const file of files) {
      formData.append('files', file)
    }
    // Don't set Content-Type for FormData - axios will set it automatically with boundary
    return client.post('/process-receipts-batch', formData, {
      params: { ocr_engine: ocrEngine, language },
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
    return client.post('/ledger/manual', entryData, {
      headers: {
        'Content-Type': 'application/json',
      }
    })
  },

  // Get reconciliation status for a transaction
  async getReconciliation(recordId) {
    return client.get(`/ledger/${recordId}/reconciliation`)
  },

  // Link two transactions
  async linkTransactions(recordId1, recordId2, relationship = 'counterparty') {
    return client.post(`/ledger/${recordId1}/link/${recordId2}`, null, {
      params: { relationship }
    })
  },

  // Toggle perspective for a transaction
  async togglePerspective(recordId) {
    return client.post(`/ledger/${recordId}/perspective/toggle`)
  },

  // Auth endpoints
  async login(email, password) {
    return client.post('/auth/login', { email, password }, {
      headers: {
        'Content-Type': 'application/json',
      }
    })
  },

  async signup(email, password, companyName) {
    return client.post('/auth/signup', { email, password, company_name: companyName }, {
      headers: {
        'Content-Type': 'application/json',
      }
    })
  },

  async getCurrentUser() {
    return client.get('/auth/me')
  },

  // Claim Rights endpoints
  async createClaimRight(claimRightData) {
    return client.post('/claim-rights', claimRightData, {
      headers: {
        'Content-Type': 'application/json',
      }
    })
  },

  async getClaimRights(claimType = null, status = null) {
    const params = {}
    if (claimType) params.claim_type = claimType
    if (status) params.status = status
    return client.get('/claim-rights', { params })
  },

  async getClaimRight(claimRightId) {
    return client.get(`/claim-rights/${claimRightId}`)
  },

  async cancelClaimRight(claimRightId, reason = null) {
    const params = {}
    if (reason) params.reason = reason
    return client.post(`/claim-rights/${claimRightId}/cancel`, null, { params })
  },

  async getClaimRightsSummary() {
    return client.get('/claim-rights/summary')
  },

  async processAccruals(periodStart = null, periodEnd = null, dryRun = false) {
    return client.post('/claim-rights/process-accruals', {
      period_start: periodStart,
      period_end: periodEnd,
      dry_run: dryRun
    }, {
      headers: {
        'Content-Type': 'application/json',
      }
    })
  },

  async createClaimRightFromLedger(ledgerEntryId, claimType, startDate = null, endDate = null, frequency = 'monthly') {
    const params = { claim_type: claimType, frequency }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    return client.post(`/ledger/${ledgerEntryId}/create-claim-right`, null, { params })
  },
}

export default client
