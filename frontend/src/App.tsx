/**
 * 主应用组件
 */

import { useState, useEffect, useRef } from 'react'
import { Settings, Brain } from 'lucide-react'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'
import StatusBar from './components/StatusBar'
import SettingsModal from './components/SettingsModal'
import { getStatus, chatStream, rebuildIndex } from './api/client'
import type { Message, ToolCall, Citation, SystemStatus } from './types'

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [localRatio, setLocalRatio] = useState(0.8)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 加载系统状态
  useEffect(() => {
    loadStatus()
  }, [])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadStatus = async () => {
    try {
      const data = await getStatus()
      setStatus(data)
    } catch (error) {
      console.error('加载状态失败:', error)
    }
  }

  const handleRebuildIndex = async () => {
    if (!confirm('确定要重建索引吗？这可能需要几分钟时间。')) return

    try {
      await rebuildIndex()
      alert('索引重建成功！')
      await loadStatus()
    } catch (error) {
      alert('索引重建失败: ' + (error as Error).message)
    }
  }

  const handleSendMessage = async (content: string) => {
    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    // 创建助手消息
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      toolCalls: [],
      citations: [],
      timestamp: new Date()
    }

    setMessages(prev => [...prev, assistantMessage])

    try {
      // 词边界安全缓冲 + 微批刷新，减少半词渲染与频繁重绘
      let pendingText = ''
      let flushScheduled = false

      const flush = () => {
        // 仅在安全边界输出，避免半词导致重复前缀；过长内容走长度回退
        const lastChar = pendingText[pendingText.length - 1] || ''
        const isSafeBoundary = /[\s\p{P}]/u.test(lastChar) || pendingText.length > 64
        if (!isSafeBoundary) return

        const toAppend = pendingText
        pendingText = ''
        setMessages(prev => {
          const newMessages = [...prev]
          const lastMsg = newMessages[newMessages.length - 1]
          lastMsg.content += toAppend
          return newMessages
        })
      }
      // 流式接收响应
      for await (const event of chatStream(content, localRatio)) {
        if (event.type === 'tool_call') {
          // 更新工具调用状态
          setMessages(prev => {
            const newMessages = [...prev]
            const lastMsg = newMessages[newMessages.length - 1]
            const toolCall: ToolCall = {
              tool: event.tool,
              status: event.status,
              count: event.count,
              timestamp: new Date()
            }
            const existingIndex = lastMsg.toolCalls?.findIndex(t => t.tool === event.tool)
            if (existingIndex !== undefined && existingIndex >= 0) {
              lastMsg.toolCalls![existingIndex] = toolCall
            } else {
              lastMsg.toolCalls = [...(lastMsg.toolCalls || []), toolCall]
            }
            return newMessages
          })
        } else if (event.type === 'citations') {
          // 设置引用
          setMessages(prev => {
            const newMessages = [...prev]
            const lastMsg = newMessages[newMessages.length - 1]
            lastMsg.citations = event.data as Citation[]
            return newMessages
          })
        } else if (event.type === 'text') {
          // 累积文本片段，使用 requestAnimationFrame 微批刷新以降低闪烁
          pendingText += event.content
          if (!flushScheduled) {
            flushScheduled = true
            requestAnimationFrame(() => {
              flushScheduled = false
              flush()
            })
          }
        }
      }
      // 结束时刷新任何未输出的缓冲文本
      if (pendingText) {
        setMessages(prev => {
          const newMessages = [...prev]
          const lastMsg = newMessages[newMessages.length - 1]
          lastMsg.content += pendingText
          return newMessages
        })
      }
    } catch (error) {
      console.error('请求失败:', error)
      
      setMessages(prev => {
        const newMessages = [...prev]
        const lastMsg = newMessages[newMessages.length - 1]
        lastMsg.content = '❌ 抱歉，请求处理失败: ' + (error as Error).message
        return newMessages
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900">
      {/* 顶部栏 */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Brain size={32} className="text-blue-500" />
          <div>
            <h1 className="text-xl font-bold text-white">AI Digital</h1>
            <p className="text-sm text-gray-400">智能笔记检索系统</p>
          </div>
        </div>
        
        <button
          onClick={() => setIsSettingsOpen(true)}
          className="text-gray-400 hover:text-white transition-colors"
        >
          <Settings size={24} />
        </button>
      </div>

      {/* 状态栏 */}
      <StatusBar status={status} onRefresh={handleRebuildIndex} />

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="text-center text-gray-500 mt-20">
              <Brain size={64} className="mx-auto mb-4 opacity-20" />
              <h2 className="text-2xl font-semibold mb-2">开始对话</h2>
              <p className="text-sm">
                向我提问关于你笔记中的任何内容
              </p>
              <div className="mt-8 grid grid-cols-2 gap-4 max-w-2xl mx-auto">
                <button
                  onClick={() => handleSendMessage('我的笔记里有哪些关于 Python 的内容？')}
                  className="bg-gray-800 hover:bg-gray-700 text-left p-4 rounded-lg transition-colors"
                >
                  <p className="text-white font-medium mb-1">📚 查找笔记</p>
                  <p className="text-gray-400 text-sm">我的笔记里有哪些关于 Python 的内容？</p>
                </button>
                
                <button
                  onClick={() => handleSendMessage('如何提高代码性能？')}
                  className="bg-gray-800 hover:bg-gray-700 text-left p-4 rounded-lg transition-colors"
                >
                  <p className="text-white font-medium mb-1">💡 混合检索</p>
                  <p className="text-gray-400 text-sm">如何提高代码性能？</p>
                </button>
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => {
              const isStreamingMsg =
                isLoading &&
                idx === messages.length - 1 &&
                msg.role === 'assistant' &&
                msg.content.length === 0
              return (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  isStreaming={isStreamingMsg}
                />
              )
            })
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 输入框 */}
      <ChatInput onSend={handleSendMessage} disabled={isLoading} />

      {/* 设置弹窗 */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        localRatio={localRatio}
        onLocalRatioChange={setLocalRatio}
      />
    </div>
  )
}

export default App
