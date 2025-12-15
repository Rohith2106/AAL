import { ref, computed } from 'vue'

// Current locale state - persisted in localStorage
const currentLocale = ref(localStorage.getItem('locale') || 'en')

// Translation dictionaries
const translations = {
  en: {
    // Navigation
    nav: {
      accounting: 'Accounting',
      automation: 'Automation',
      uploadReceipt: 'Upload Receipt',
      transactions: 'Transactions',
      aiAssistant: 'AI Assistant'
    },
    // Upload page
    upload: {
      title: 'Upload Receipt',
      subtitle: 'Drag and drop your files to process them automatically',
      dropHere: 'Drop your receipts here',
      browse: 'or click to browse files',
      processing: 'Processing...',
      complete: 'Complete!',
      processingOf: 'Processing {current} of {total} files...',
      ocrEngine: 'OCR Engine',
      ocrLanguage: 'OCR Language',
      recommended: 'Recommended',
      uploadMore: 'Upload More Files',
      processingResult: 'Processing Result',
      processingResults: 'Processing Results',
      validated: 'Validated',
      pendingReview: 'Pending Review',
      successful: 'successful',
      failed: 'failed',
      vendor: 'Vendor',
      total: 'Total',
      date: 'Date',
      category: 'Category',
      confidence: 'Confidence',
      validationIssues: 'Validation Issues',
      aiAnalysis: 'AI Analysis',
      uploadAnother: 'Upload Another',
      approveAddLedger: 'Approve & Add to Ledger',
      english: 'English',
      japanese: 'Japanese',
      both: 'Both'
    },
    // Ledger page
    ledger: {
      title: 'Transaction Ledger',
      subtitle: 'Manage and track your financial records',
      exportCsv: 'Export CSV',
      addManual: 'Add Manual Entry',
      total: 'Total',
      amount: 'Amount',
      validated: 'Validated',
      pending: 'Pending',
      status: 'Status',
      vendor: 'Vendor',
      date: 'Date',
      confidence: 'Confidence',
      actions: 'Actions',
      clearFilters: 'Clear Filters',
      noTransactions: 'No transactions found',
      uploadToStart: 'Upload a receipt to get started',
      allStatuses: 'All Statuses',
      rejected: 'Rejected',
      searchVendor: 'Search vendor...',
      usdConverted: 'USD (converted)',
      deleteConfirm: 'Delete Transaction?',
      deleteWarning: 'This action cannot be undone. This will permanently delete the transaction from your ledger.',
      cancel: 'Cancel',
      delete: 'Delete',
      transactionDetails: 'Transaction Details',
      paymentMethod: 'Payment Method',
      description: 'Description',
      lineItems: 'Line Items',
      qty: 'Qty',
      price: 'Price',
      validationIssues: 'Validation Issues',
      validateTransaction: 'Validate Transaction',
      rejectTransaction: 'Reject Transaction',
      addManualTransaction: 'Add Manual Transaction',
      enterDetails: 'Enter transaction details manually',
      vendorRequired: 'Vendor *',
      dateRequired: 'Date *',
      currencyRequired: 'Currency *',
      tax: 'Tax',
      totalRequired: 'Total *',
      invoiceNumber: 'Invoice Number',
      optional: 'Optional',
      transactionDescription: 'Transaction description',
      addItem: '+ Add Item',
      itemName: 'Item Name',
      unitPrice: 'Unit Price',
      noLineItems: 'No line items. Click "Add Item" to add line items.',
      creating: 'Creating...',
      createTransaction: 'Create Transaction'
    },
    // Transaction detail
    detail: {
      title: 'Transaction Details',
      loading: 'Loading...',
      notFound: 'Transaction not found',
      vendor: 'Vendor',
      date: 'Date',
      total: 'Total',
      status: 'Status',
      lineItems: 'Line Items',
      items: 'items',
      item: 'Item',
      quantity: 'Quantity',
      unitPrice: 'Unit Price',
      subtotal: 'Subtotal',
      tax: 'Tax',
      validate: 'Validate Transaction',
      reject: 'Reject Transaction',
      delete: 'Delete Transaction',
      noLineItems: 'No line items available'
    },
    // Accounting / Double-Entry
    accounting: {
      journalEntry: 'Journal Entry',
      doubleEntry: 'Double-Entry Accounting',
      debit: 'Debit',
      credit: 'Credit',
      account: 'Account',
      accountCode: 'Code',
      accountName: 'Account Name',
      accountType: 'Type',
      balance: 'Balance',
      totalDebits: 'Total Debits',
      totalCredits: 'Total Credits',
      balanced: 'Balanced',
      unbalanced: 'Unbalanced',
      reference: 'Reference',
      noJournalEntry: 'No journal entry generated yet'
    },
    // Chat interface
    chat: {
      title: 'AI Assistant',
      subtitle: 'Ask questions about your financial data',
      model: 'Model',
      placeholder: 'Ask about receipts, invoices, or ledger entries...',
      sources: 'Sources',
      match: 'match',
      greeting: 'Hello! I can help you query your ledger and receipts. Ask me anything about your transactions, vendors, or amounts.',
      error: 'Sorry, I encountered an error. Please try again.',
      totalSpent: 'What is the total amount spent?',
      lastMonth: 'Show me all transactions from last month',
      highestVendor: 'Which vendor has the highest total?',
      taxOver: 'Find receipts with tax over $100'
    },
    // Common
    common: {
      na: 'N/A',
      cancel: 'Cancel',
      save: 'Save',
      delete: 'Delete',
      confirm: 'Confirm',
      back: 'Back'
    },
    // Language toggle
    language: {
      english: 'English',
      japanese: '日本語',
      toggle: 'Language'
    }
  },
  ja: {
    // Navigation
    nav: {
      accounting: '会計',
      automation: '自動化',
      uploadReceipt: 'レシートをアップロード',
      transactions: '取引履歴',
      aiAssistant: 'AIアシスタント'
    },
    // Upload page
    upload: {
      title: 'レシートをアップロード',
      subtitle: 'ファイルをドラッグ＆ドロップして自動処理します',
      dropHere: 'ここにレシートをドロップ',
      browse: 'またはクリックしてファイルを選択',
      processing: '処理中...',
      complete: '完了！',
      processingOf: '{total}件中{current}件を処理中...',
      ocrEngine: 'OCRエンジン',
      ocrLanguage: 'OCR言語',
      recommended: '推奨',
      uploadMore: '他のファイルをアップロード',
      processingResult: '処理結果',
      processingResults: '処理結果',
      validated: '承認済み',
      pendingReview: '確認待ち',
      successful: '成功',
      failed: '失敗',
      vendor: '取引先',
      total: '合計',
      date: '日付',
      category: 'カテゴリ',
      confidence: '信頼度',
      validationIssues: '検証の問題',
      aiAnalysis: 'AI分析',
      uploadAnother: '別のファイルをアップロード',
      approveAddLedger: '承認して台帳に追加',
      english: '英語',
      japanese: '日本語',
      both: '両方'
    },
    // Ledger page
    ledger: {
      title: '取引台帳',
      subtitle: '財務記録を管理・追跡する',
      exportCsv: 'CSVエクスポート',
      addManual: '手動入力を追加',
      total: '合計',
      amount: '金額',
      validated: '承認済み',
      pending: '保留中',
      status: 'ステータス',
      vendor: '取引先',
      date: '日付',
      confidence: '信頼度',
      actions: '操作',
      clearFilters: 'フィルタをクリア',
      noTransactions: '取引が見つかりません',
      uploadToStart: 'レシートをアップロードして開始',
      allStatuses: 'すべてのステータス',
      rejected: '却下',
      searchVendor: '取引先を検索...',
      usdConverted: 'USD（換算済）',
      deleteConfirm: '取引を削除しますか？',
      deleteWarning: 'この操作は元に戻せません。取引は台帳から完全に削除されます。',
      cancel: 'キャンセル',
      delete: '削除',
      transactionDetails: '取引詳細',
      paymentMethod: '支払方法',
      description: '説明',
      lineItems: '明細項目',
      qty: '数量',
      price: '単価',
      validationIssues: '検証の問題',
      validateTransaction: '取引を承認',
      rejectTransaction: '取引を却下',
      addManualTransaction: '手動取引を追加',
      enterDetails: '取引の詳細を手動で入力',
      vendorRequired: '取引先 *',
      dateRequired: '日付 *',
      currencyRequired: '通貨 *',
      tax: '税',
      totalRequired: '合計 *',
      invoiceNumber: '請求書番号',
      optional: '任意',
      transactionDescription: '取引の説明',
      addItem: '+ 項目を追加',
      itemName: '品目名',
      unitPrice: '単価',
      noLineItems: '明細項目がありません。「項目を追加」をクリックして追加してください。',
      creating: '作成中...',
      createTransaction: '取引を作成'
    },
    // Transaction detail
    detail: {
      title: '取引詳細',
      loading: '読み込み中...',
      notFound: '取引が見つかりません',
      vendor: '取引先',
      date: '日付',
      total: '合計',
      status: 'ステータス',
      lineItems: '明細項目',
      items: '件',
      item: '品目',
      quantity: '数量',
      unitPrice: '単価',
      subtotal: '小計',
      tax: '税',
      validate: '取引を承認',
      reject: '取引を却下',
      delete: '取引を削除',
      noLineItems: '明細項目がありません'
    },
    // Accounting / Double-Entry
    accounting: {
      journalEntry: '仕訳',
      doubleEntry: '複式簿記',
      debit: '借方',
      credit: '貸方',
      account: '勘定科目',
      accountCode: 'コード',
      accountName: '科目名',
      accountType: '種類',
      balance: '残高',
      totalDebits: '借方合計',
      totalCredits: '貸方合計',
      balanced: 'バランス済',
      unbalanced: 'アンバランス',
      reference: '参照',
      noJournalEntry: '仕訳がまだ生成されていません'
    },
    // Chat interface
    chat: {
      title: 'AIアシスタント',
      subtitle: '財務データについて質問してください',
      model: 'モデル',
      placeholder: 'レシート、請求書、台帳について質問...',
      sources: '情報源',
      match: '一致',
      greeting: 'こんにちは！台帳やレシートについてお手伝いします。取引、取引先、金額について何でもお聞きください。',
      error: 'エラーが発生しました。もう一度お試しください。',
      totalSpent: '合計支出額はいくらですか？',
      lastMonth: '先月の取引をすべて表示',
      highestVendor: '最も支出額が多い取引先は？',
      taxOver: '税金が100ドル以上のレシートを検索'
    },
    // Common
    common: {
      na: 'なし',
      cancel: 'キャンセル',
      save: '保存',
      delete: '削除',
      confirm: '確認',
      back: '戻る'
    },
    // Language toggle
    language: {
      english: 'English',
      japanese: '日本語',
      toggle: '言語'
    }
  }
}

/**
 * Vue composable for internationalization
 * @returns {Object} i18n utilities
 */
export function useI18n() {
  const locale = computed(() => currentLocale.value)
  
  /**
   * Get translation for a key
   * @param {string} key - Dot-notated key (e.g., 'nav.uploadReceipt')
   * @returns {string} Translated string or key if not found
   */
  const t = (key) => {
    const keys = key.split('.')
    let value = translations[currentLocale.value]
    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k]
      } else {
        return key // Return key if translation not found
      }
    }
    return value || key
  }
  
  /**
   * Set the current locale
   * @param {string} newLocale - Locale code ('en' or 'ja')
   */
  const setLocale = (newLocale) => {
    currentLocale.value = newLocale
    localStorage.setItem('locale', newLocale)
    // Update document lang attribute
    document.documentElement.lang = newLocale
  }
  
  /**
   * Toggle between English and Japanese
   */
  const toggleLocale = () => {
    setLocale(currentLocale.value === 'en' ? 'ja' : 'en')
  }
  
  /**
   * Check if current locale is Japanese
   */
  const isJapanese = computed(() => currentLocale.value === 'ja')
  
  return {
    locale,
    t,
    setLocale,
    toggleLocale,
    isJapanese
  }
}

export default useI18n
