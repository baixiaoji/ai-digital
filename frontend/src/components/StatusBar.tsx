/**
 * 状态栏组件
 */

import { Database, RefreshCw } from 'lucide-react'
import type { SystemStatus } from '../types'

interface Props {
  status: SystemStatus | null
  onRefresh: () => void
}

export default function StatusBar({ status, onRefresh }: Props) {
  if (!status) return null

  return (
    <div className="bg-gray-800 border-b border-gray-700 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6 text-sm text-gray-400">
          <div className="flex items-center gap-2">
            <Database size={16} />
            <span>已索引: {status.indexed_files.toLocaleString()} 个文件</span>
          </div>
          <div>
            <span>分块: {status.total_chunks.toLocaleString()}</span>
          </div>
          <div>
            <span>索引大小: {status.index_size_mb} MB</span>
          </div>
          <div className="text-xs text-gray-500">
            更新于: {new Date(status.last_update).toLocaleString('zh-CN')}
          </div>
        </div>
        
        <button
          onClick={onRefresh}
          className="text-gray-400 hover:text-white flex items-center gap-2 text-sm transition-colors"
        >
          <RefreshCw size={16} />
          重建索引
        </button>
      </div>
    </div>
  )
}
