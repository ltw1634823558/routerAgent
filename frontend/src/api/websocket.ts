// WebSocket 连接管理
export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private onMessage: (data: string) => void
  private onError?: (error: Event) => void
  private onClose?: () => void

  constructor(
    agentType: string,
    onMessage: (data: string) => void,
    onError?: (error: Event) => void,
    onClose?: () => void
  ) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    this.url = `${protocol}//${window.location.host}/ws/agent/${agentType}`
    this.onMessage = onMessage
    this.onError = onError
    this.onClose = onClose
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket 连接成功')
        resolve()
      }

      this.ws.onmessage = (event) => {
        this.onMessage(event.data)
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket 错误:', error)
        this.onError?.(error)
        reject(error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket 连接关闭')
        this.onClose?.()
      }
    })
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.error('WebSocket 未连接')
    }
  }

  close() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}
