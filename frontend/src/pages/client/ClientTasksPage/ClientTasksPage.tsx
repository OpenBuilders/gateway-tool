import { PageLayout, TelegramBackButton, TelegramMainButton } from '@components'
import { useAppNavigation, useError } from '@hooks'
import { ROUTES_NAME } from '@routes'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { LocalStorageService } from '@services'
import { useApp, useAppActions, useChat, useChatActions, useUser } from '@store'

import { Skeleton } from './Skeleton'
import { ChatConditions, ChatHeader } from './components'
import { createButtonText, formatConditions } from './helpers'
import { FormattedConditions } from './types'

const webApp = window.Telegram.WebApp

export const ClientTasksPage = () => {
  const { clientChatSlug } = useParams<{ clientChatSlug: string }>()
  const { notFound } = useError()

  const { isLoading } = useApp()
  const { toggleIsLoadingAction } = useAppActions()

  const [isChecking, setIsChecking] = useState(false)
  const [sortedConditions, setSortedConditions] =
    useState<FormattedConditions | null>(null)

  const { appNavigate } = useAppNavigation()

  const { fetchUserChatAction } = useChatActions()
  const { chat, rules, chatWallet } = useChat()
  const { user } = useUser()

  const fetchUserChat = async () => {
    if (!clientChatSlug) return

    try {
      await fetchUserChatAction(clientChatSlug)
    } catch (error) {
      console.error(error)
      notFound()
    }
  }

  useEffect(() => {
    if (!clientChatSlug) return
    toggleIsLoadingAction(true)
    fetchUserChat()
    toggleIsLoadingAction(false)
  }, [clientChatSlug])

  useEffect(() => {
    if (chat && !chat?.isEnabled) {
      appNavigate({
        path: ROUTES_NAME.CLIENT_CHAT_HIDDEN,
        params: { clientChatSlug },
      })
      return
    }
  }, [chat])

  useEffect(() => {
    if (!rules) return
    const sortedConditions = formatConditions(rules)
    setSortedConditions(sortedConditions)
  }, [rules])

  if (isLoading || !chat || !rules || !sortedConditions) {
    return (
      <PageLayout>
        <TelegramBackButton />
        <Skeleton />
      </PageLayout>
    )
  }

  // const hideButton = !sortedConditions?.whitelist?.[0]?.isEligible

  const buttonAction = async () => {
    const emojiCondition = rules.find((rule) => rule.type === 'emoji')
    const whitelistCondition = rules.find((rule) => rule.type === 'whitelist')
    if (emojiCondition && !whitelistCondition) {
      const checkEmojiStatusCompleted = LocalStorageService.getItem(
        `emojiStatusCompleted_${chat?.slug}_${emojiCondition.id}`
      )
      if (!checkEmojiStatusCompleted) {
        return
      }
    }

    if (chat.isEligible) {
      appNavigate({
        path: ROUTES_NAME.CLIENT_JOIN,
        params: { clientChatSlug },
      })
      return
    }

    if (chatWallet) {
      setIsChecking(true)
      await fetchUserChat()
      setTimeout(() => {
        setIsChecking(false)
        webApp?.HapticFeedback?.impactOccurred('soft')
      }, 400)
      return
    }

    if (user?.wallets.length) {
      appNavigate({
        path: ROUTES_NAME.CLIENT_WALLETS_LIST,
        params: { clientChatSlug },
      })
      return
    }

    appNavigate({
      path: ROUTES_NAME.CLIENT_TASKS,
      params: { clientChatSlug },
      queryParams: { connectWallet: 'true' },
    })
  }

  const buttonText = createButtonText({
    chatWallet,
    rules,
    isChecking,
    chat,
  })

  return (
    <PageLayout>
      <TelegramBackButton />
      <TelegramMainButton
        text={buttonText}
        isVisible={!!buttonText}
        disabled={isLoading || isChecking}
        onClick={buttonAction}
        loading={isLoading || isChecking}
      />
      <ChatHeader />
      <ChatConditions conditions={sortedConditions} />
    </PageLayout>
  )
}
