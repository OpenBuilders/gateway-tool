import {
  Block,
  PageLayout,
  TelegramBackButton,
  TelegramMainButton,
  Text,
} from '@components'
import { useAppNavigation, useError } from '@hooks'
import { ROUTES_NAME } from '@routes'
import { useEffect } from 'react'
import { useParams } from 'react-router-dom'

import { useApp, useAppActions, useChat, useChatActions } from '@store'

import { ChatConditions, ChatHeader } from './components'

const webApp = window.Telegram.WebApp

export const ChatPage = () => {
  const { chatSlug } = useParams<{ chatSlug: string }>()
  const { appNavigate } = useAppNavigation()

  const { isLoading } = useApp()
  const { toggleIsLoadingAction } = useAppActions()

  const { adminChatNotFound } = useError()

  const { rules } = useChat()
  const { fetchChatAction } = useChatActions()

  const fetchChat = async () => {
    if (!chatSlug) return
    try {
      await fetchChatAction(chatSlug)
    } catch (error) {
      console.error(error)
      adminChatNotFound()
    }
  }

  useEffect(() => {
    toggleIsLoadingAction(true)
    fetchChat()
    toggleIsLoadingAction(false)
  }, [chatSlug])

  if (isLoading) return null

  const showMainButton = rules && rules?.length > 0

  const handleOpenGroupChat = () => {
    if (!chatSlug) return
    webApp.openTelegramLink(`https://t.me/${chatSlug}`)
  }

  return (
    <PageLayout>
      <TelegramBackButton
        onClick={() => appNavigate({ path: ROUTES_NAME.MAIN })}
      />
      <TelegramMainButton
        hidden={!showMainButton}
        text="Open Group Chat"
        onClick={handleOpenGroupChat}
      />
      <ChatHeader />
      <ChatConditions />
      <Block margin="top" marginValue="auto">
        <Text type="caption" align="center" color="tertiary">
          To delete this page from Gateway,
          <br />
          remove @gateway_bot from admins
        </Text>
      </Block>
    </PageLayout>
  )
}
