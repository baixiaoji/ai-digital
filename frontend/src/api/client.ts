/**
 * API 客户端
 */

import type { SystemStatus, SearchResult } from "../types";

const API_BASE = "/api";

/**
 * 获取系统状态
 */
export async function getStatus(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE}/status`);
  if (!response.ok) {
    throw new Error("获取状态失败");
  }
  return response.json();
}

/**
 * 搜索（非流式）
 */
export async function search(
  query: string,
  localRatio: number = 0.8
): Promise<SearchResult[]> {
  const response = await fetch(
    `${API_BASE}/search?query=${encodeURIComponent(
      query
    )}&local_ratio=${localRatio}`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    throw new Error("搜索失败");
  }

  const data = await response.json();
  return data.results;
}

/**
 * Chat 流式接口
 */
export async function* chatStream(query: string, localRatio: number = 0.8) {
  const response = await fetch(
    `${API_BASE}/chat?query=${encodeURIComponent(
      query
    )}&local_ratio=${localRatio}`,
    {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
      },
    }
  );

  if (!response.ok) {
    throw new Error("请求失败");
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error("无法读取响应流");
  }

  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // 按行分割
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const dataStr = line.slice(6);

        if (dataStr === "{'type': 'done'}") {
          return;
        }

        try {
          // 修复单引号 JSON
          const jsonStr = dataStr.replace(/'/g, '"');
          const data = JSON.parse(jsonStr);
          yield data;
        } catch (e) {
          console.warn("解析 SSE 数据失败:", dataStr, e);
        }
      }
    }
  }
}

/**
 * 重建索引
 */
export async function rebuildIndex(): Promise<void> {
  const response = await fetch(`${API_BASE}/rebuild-index`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("重建索引失败");
  }
}

/**
 * 打开本地文件（通过 Logseq URL Scheme）
 * 格式：logseq://graph/graph-name?page=<page-name>
 *
 * @param filePath 文件路径，例如：/Users/xxx/logseq-file/pages/向 AI 公司 blog 学习.md
 */
export function openInLogseq(filePath: string) {
  // 1. 提取页面名称（去掉路径和扩展名）
  let fileName = filePath.split("/").pop()?.replace(/\.md$/, "") || "";

  // 2. 检查是否为日期格式（yyyy_MM_dd 或 yyyy-MM-dd）并转换
  const datePattern = /^(\d{4})[_-](\d{2})[_-](\d{2})$/;
  const match = fileName.match(datePattern);

  if (match) {
    const [, year, month, day] = match;
    // 转换为 MMM do, yyyy 格式（例如：Dec 8th, 2025）
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    const monthNames = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    const monthName = monthNames[date.getMonth()];
    const dayNum = date.getDate();

    // 添加序数后缀（1st, 2nd, 3rd, 4th, etc.）
    const suffix = (dayNum: number) => {
      if (dayNum >= 11 && dayNum <= 13) return "th";
      switch (dayNum % 10) {
        case 1:
          return "st";
        case 2:
          return "nd";
        case 3:
          return "rd";
        default:
          return "th";
      }
    };

    fileName = `${monthName} ${dayNum}${suffix(dayNum)}, ${year}`;
  }

  // 3. 构建 Logseq URL：logseq://graph/logseq-file?page=<encodeURI(fileName)>
  // 使用 encodeURI 而不是 encodeURIComponent，保留某些特殊字符
  const url = `logseq://graph/logseq-file?page=${encodeURI(fileName)}`;

  console.log("[Logseq] Opening:", url);
  window.open(url, "_blank");
}
