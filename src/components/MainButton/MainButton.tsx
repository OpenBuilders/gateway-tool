import { useEffect } from 'react'

interface MainButtonProps {
  text: string
  onClick: () => void
}

const webApp = window.Telegram?.WebApp
const mainButton = webApp?.MainButton

export const TelegramMainButton = ({ text, onClick }: MainButtonProps) => {
  useEffect(() => {
    if (!webApp || !mainButton) return
    const { button_color, button_text_color } = webApp.themeParams

    mainButton.setParams({
      color: button_color,
      text_color: button_text_color,
    })
    mainButton.show()

    const handleMainButtonClick = () => onClick()

    mainButton.onClick(handleMainButtonClick)

    return () => {
      mainButton.offClick(handleMainButtonClick)
      mainButton.hide()
    }
  }, [text])

  useEffect(() => {
    if (!webApp || !mainButton) return

    mainButton.setParams({
      text: text || 'Continue',
    })
  }, [text])

  if (webApp.platform === 'unknown' && process.env.NODE_ENV !== 'production') {
    return (
      <button
        onClick={onClick}
        style={{
          width: '100%',
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 1000,
          height: '56px',
        }}
      >
        {text}
      </button>
    )
  }

  return null
}
