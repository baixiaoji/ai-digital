/**
 * 设置弹窗组件
 */

import { X, Settings as SettingsIcon } from 'lucide-react'
import { useState } from 'react'

interface Props {
  isOpen: boolean
  onClose: () => void
  localRatio: number
  onLocalRatioChange: (value: number) => void
}

export default function SettingsModal({ isOpen, onClose, localRatio, onLocalRatioChange }: Props) {
  const [tempRatio, setTempRatio] = useState(localRatio)

  if (!isOpen) return null

  const handleSave = () => {
    onLocalRatioChange(tempRatio)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-md p-6">
        {/* 标题 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <SettingsIcon size={24} className="text-blue-500" />
            <h2 className="text-xl font-semibold text-white">设置</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* 设置项 */}
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              本地/网络结果比例
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={tempRatio}
                onChange={(e) => setTempRatio(parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-white font-mono w-16 text-right">
                {Math.round(tempRatio * 100)}%
              </span>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>网络优先</span>
              <span>本地优先</span>
            </div>
          </div>

          <div className="bg-gray-700/50 rounded p-3 text-sm text-gray-300">
            <p className="mb-2">💡 提示：</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>本地比例越高，优先返回笔记中的内容</li>
              <li>网络比例越高，更多补充最新网络资料</li>
              <li>推荐保持 80% 本地 + 20% 网络</li>
            </ul>
          </div>
        </div>

        {/* 按钮 */}
        <div className="mt-6 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded transition-colors"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  )
}
