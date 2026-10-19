interface TelegramWebApp {
  initData: string
  colorScheme: 'light' | 'dark'
  themeParams: Record<string, string>
  ready(): void
  expand(): void
  onEvent(eventType: 'themeChanged', callback: () => void): void
  offEvent(eventType: 'themeChanged', callback: () => void): void
}

interface Window {
  Telegram?: { WebApp?: TelegramWebApp }
}
