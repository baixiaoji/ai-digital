/**
 * Chat 消息组件
 */

import { User, Bot, ExternalLink, FileText, Tag, Loader2 } from "lucide-react";
import { Streamdown, parseMarkdownIntoBlocks } from "streamdown";
import type { Message } from "../types";
import { openInLogseq } from "../api/client";

interface Props {
  message: Message;
  isStreaming?: boolean;
}

export default function ChatMessage({ message, isStreaming = false }: Props) {
  const isUser = message.role === "user";

  console.log('ChatMessage', message)
  return (
    <div
      className={`flex gap-4 ${isUser ? "justify-end" : "justify-start"} mb-6`}
    >
      {/* 头像 */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
          <Bot size={20} className="text-white" />
        </div>
      )}

      {/* 消息内容 */}
      <div className={`flex-1 max-w-3xl ${isUser ? "flex justify-end" : ""}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-100"
          }`}
        >
          {/* 工具调用指示器 */}
          {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mb-3 space-y-2">
              {message.toolCalls.map((tool, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 text-sm text-gray-400"
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      tool.status === "running"
                        ? "bg-yellow-500 animate-pulse"
                        : tool.status === "completed"
                        ? "bg-green-500"
                        : "bg-red-500"
                    }`}
                  />
                  <span>
                    {tool.tool === "local_search"
                      ? "🔍 本地检索"
                      : tool.tool === "note_search"
                      ? "📓 笔记检索"
                      : tool.tool === "notebook_search"
                      ? "📔 笔记本检索"
                      : tool.tool === "web_search"
                      ? "🌐 网络搜索"
                      : `🔧 ${tool.tool}`}
                    {tool.status === "completed" &&
                      tool.count !== undefined &&
                      ` (${tool.count} 条)`}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* 等待整合提示：在工具完成后、首段文本返回前显示 */}
          {!isUser &&
            isStreaming &&
            (!message.content || message.content.length === 0) &&
            (!message.toolCalls ||
              message.toolCalls.length === 0 ||
              message.toolCalls.every((tc) => tc.status === "completed")) && (
            <div className="mb-2 text-sm text-gray-400 flex items-center gap-2">
              <Loader2 size={16} className="animate-spin" />
              正在整合答案...
            </div>
          )}

          {/* 消息文本 - 使用 Streamdown 支持流式 Markdown 渲染 */}
          <div className="prose prose-invert prose-sm max-w-none">
            {parseMarkdownIntoBlocks(message.content).map((block, idx) => (
              <Streamdown
                key={idx}
                mode="streaming"
                parseIncompleteMarkdown={true}
              >
                {block}
              </Streamdown>
            ))}
          </div>

          {/* 引用列表 */}
          {!isUser && message.citations && message.citations.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="text-xs text-gray-400 mb-2">📎 引用来源</div>
              <div className="space-y-2">
                {message.citations.map((citation) => (
                  <div
                    key={citation.id}
                    className="text-sm bg-gray-700/50 rounded p-2"
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-gray-400">[{citation.id}]</span>

                      {citation.source === "local" ? (
                        <div className="flex-1">
                          <button
                            onClick={() =>
                              citation.file_path &&
                              openInLogseq(citation.file_path)
                            }
                            className="text-blue-400 hover:text-blue-300 flex items-center gap-1"
                          >
                            <FileText size={14} />
                            {citation.title}
                          </button>
                          {citation.tags && citation.tags.length > 0 && (
                            <div className="flex gap-1 mt-1 flex-wrap">
                              {citation.tags.map((tag, idx) => (
                                <span
                                  key={idx}
                                  className="text-xs bg-gray-600 px-2 py-0.5 rounded flex items-center gap-1"
                                >
                                  <Tag size={10} />
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <a
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-400 hover:text-blue-300 flex items-center gap-1 flex-1"
                        >
                          <ExternalLink size={14} />
                          {citation.title}
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 时间戳 */}
          <div className="mt-2 text-xs text-gray-500">
            {message.timestamp.toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        </div>
      </div>

      {/* 用户头像 */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center">
          <User size={20} className="text-white" />
        </div>
      )}
    </div>
  );
}
