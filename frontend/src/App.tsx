import { ThemeContext } from '@context'
import { useAppNavigation } from '@hooks'
import '@styles/index.scss'
import { TonConnectUIProvider } from '@tonconnect/ui-react'
import { checkStartAppParams } from '@utils'
import { useContext, useEffect } from 'react'
import { useLocation, useParams } from 'react-router-dom'

import config from '@config'
import { useUser, useUserActions } from '@store'

import Routes, { ROUTES_NAME } from './Routes'

const webApp = window.Telegram?.WebApp

function App() {
  const { clientChatSlug } = useParams<{ clientChatSlug: string }>()
  const { appNavigate } = useAppNavigation()
  const { darkTheme } = useContext(ThemeContext)

  const location = useLocation()

  const { authenticateUserAction, fetchUserAction } = useUserActions()
  const { isAuthenticated } = useUser()

  const authenticateUser = async () => {
    try {
      await authenticateUserAction()
    } catch (error) {
      console.error(error)
    }
  }

  const fetchUser = async () => {
    try {
      await fetchUserAction()
    } catch (error) {
      console.error(error)
    }
  }

  useEffect(() => {
    document.documentElement.setAttribute(
      'data-theme',
      darkTheme ? 'dark' : 'light'
    )

    if (darkTheme) {
      window.document.documentElement.style.backgroundColor = '#1c1c1e'
      webApp?.setHeaderColor('#1c1c1e')
      webApp?.setBackgroundColor('#1c1c1e')
      webApp?.setBottomBarColor('#1c1c1e')
    } else {
      window.document.documentElement.style.backgroundColor = '#EFEFF4'
      webApp?.setHeaderColor('#EFEFF4')
      webApp?.setBackgroundColor('#EFEFF4')
      webApp?.setBottomBarColor('#EFEFF4')
    }
  }, [darkTheme])

  useEffect(() => {
    const ch = checkStartAppParams()
    if (ch) {
      appNavigate({
        path: ROUTES_NAME.CLIENT_TASKS,
        params: {
          clientChatSlug: ch,
        },
      })
    }
  }, [])

  useEffect(() => {
    webApp.disableVerticalSwipes()
    if (!location.pathname.includes('client')) {
      webApp.expand()
    }
  }, [])

  useEffect(() => {
    if (!isAuthenticated) {
      authenticateUser()
    }
  }, [location.pathname])

  useEffect(() => {
    if (isAuthenticated) {
      fetchUser()
    }
  }, [isAuthenticated])

  console.log(import.meta.env.MODE)

  if (!isAuthenticated) return null

  return (
    <TonConnectUIProvider
      // TODO: manifest
      manifestUrl={config.tonConnectManifestUrl}
      actionsConfiguration={{
        twaReturnUrl: `https://t.me/${config.botName}/gate?startapp=ch_${clientChatSlug}`,
      }}
    >
      {Routes}
    </TonConnectUIProvider>
  )
}

export default App
