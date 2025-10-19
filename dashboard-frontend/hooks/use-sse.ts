"use client"

import { useEffect, useRef, useState } from "react"
import type { SSEMessage, ConnectionStatus } from "@/lib/types"

export function useSSE(url: string, onMessage: (message: SSEMessage) => void) {
  const [status, setStatus] = useState<ConnectionStatus>("disconnected")
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)

  useEffect(() => {
    function connect() {
      try {
        const es = new EventSource(url)
        eventSourceRef.current = es

        es.onopen = () => {
          setStatus("connected")
          reconnectAttemptsRef.current = 0
        }

        es.onmessage = (event) => {
          try {
            const message: SSEMessage = JSON.parse(event.data)
            onMessage(message)
          } catch (error) {
            console.error("[v0] Failed to parse SSE message:", error)
          }
        }

        es.onerror = () => {
          es.close()
          setStatus("reconnecting")

          // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          reconnectAttemptsRef.current++

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        }
      } catch (error) {
        console.error("[v0] Failed to create EventSource:", error)
        setStatus("disconnected")
      }
    }

    connect()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [url, onMessage])

  return status
}
