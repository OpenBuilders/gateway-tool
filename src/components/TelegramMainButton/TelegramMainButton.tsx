import { useEffect } from 'react'

interface MainButtonProps {
  text?: string
  onClick?: () => void
  hidden?: boolean
  disabled?: boolean
  isLoading?: boolean
}

const webApp = window.Telegram?.WebApp
const mainButton = webApp?.MainButton

export const TelegramMainButton = ({
  text,
  onClick,
  hidden,
  disabled,
  isLoading,
}: MainButtonProps) => {
  useEffect(() => {
    if (!webApp || !mainButton) {
      mainButton?.hide()
      return
    }

    if (!onClick || !text || hidden) {
      mainButton.hide()
      return
    }

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

    if (disabled) {
      mainButton.disable()
    } else {
      mainButton.enable()
    }
  }, [disabled])

  useEffect(() => {
    if (!webApp || !mainButton) return

    mainButton.setParams({
      text: text || 'Continue',
    })
  }, [text])

  useEffect(() => {
    if (!webApp || !mainButton) return

    if (isLoading) {
      mainButton.showProgress()
    } else {
      mainButton.hideProgress()
    }
  }, [isLoading])

  if (
    webApp.platform === 'unknown' &&
    process.env.NODE_ENV !== 'production' &&
    !hidden
  ) {
    return (
      <button
        onClick={onClick}
        style={{
          width: '100%',
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 10000000000000000,
          height: '56px',
        }}
        disabled={disabled}
      >
        {text}
      </button>
    )
  }

  return null
}
