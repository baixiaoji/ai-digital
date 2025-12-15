/**
 * 类型定义
 */

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  toolCalls?: ToolCall[]
  timestamp: Date
}

export interface Citation {
  id: number
  title: string
  source: 'local' | 'web'
  file_path?: string
  url?: string
  tags?: string[]
  created_at?: string
}

export interface ToolCall {
  tool: string
  status: 'running' | 'completed' | 'failed'
  count?: number
  timestamp: Date
}

export interface SearchResult {
  content: string
  file_path: string
  title: string
  score: number
  source: 'local' | 'web'
  chunk_id?: string
  tags?: string[]
  backlinks?: string[]
  created_at?: string
  url?: string
}

export interface SystemStatus {
  indexed_files: number
  total_chunks: number
  last_update: string
  index_size_mb: number
}
