/**
 * Chat 输入框组件
 */

import { useState, KeyboardEvent, useRef } from 'react'
import { Send, Loader2 } from 'lucide-react'

interface Props {
  onSend: (message: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const autoResize = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }

  const handleSend = () => {
    const trimmed = input.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setInput('')
      // 清空后恢复到最小高度
      requestAnimationFrame(() => autoResize())
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-700 bg-gray-800 p-4">
      <div className="max-w-4xl mx-auto flex gap-4 items-center">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={autoResize}
          onFocus={autoResize}
          placeholder="输入你的问题... (Shift+Enter 换行)"
          disabled={disabled}
          className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-3 resize-none overflow-hidden focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px]"
          rows={1}
          style={{ transition: 'height 150ms ease' }}
        />
        
        <button
          onClick={handleSend}
          disabled={disabled || !input.trim()}
          className="h-12 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg px-6 flex items-center gap-2 transition-colors"
        >
          {disabled ? (
            <>
              <Loader2 size={20} className="animate-spin" />
              处理中...
            </>
          ) : (
            <>
              <Send size={20} />
              发送
            </>
          )}
        </button>
      </div>
    </div>
  )
}
