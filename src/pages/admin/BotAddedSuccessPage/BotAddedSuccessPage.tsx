import confettiLottie from '@assets/confetti.json'
import commonStyles from '@common/styles/commonStyles.module.scss'
import {
  Block,
  Icon,
  PageLayout,
  StickerPlayer,
  TelegramBackButton,
  TelegramMainButton,
  Text,
} from '@components'
import { useAppNavigation, useError } from '@hooks'
import { ROUTES_NAME } from '@routes'
import '@styles/index.scss'
import cn from 'classnames'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { useChatActions } from '@store'

export const BotAddedSuccessPage = () => {
  const { chatSlug } = useParams<{ chatSlug: string }>()
  const { appNavigate } = useAppNavigation()
  const { fetchChatAction } = useChatActions()
  const { pageNotFound } = useError()
  const [isLoading, setIsLoading] = useState(false)

  const fetchChat = async () => {
    if (!chatSlug) return
    try {
      await fetchChatAction(chatSlug)
    } catch (error) {
      console.error(error)
      pageNotFound('Chat not found')
    }
  }

  useEffect(() => {
    setIsLoading(true)
    fetchChat()
    setIsLoading(false)
  }, [chatSlug])

  const navigateToMainPage = () => {
    appNavigate({ path: ROUTES_NAME.MAIN })
  }

  const navigateToChat = () => {
    appNavigate({
      path: ROUTES_NAME.CHAT,
      params: { chatSlug: chatSlug },
    })
  }

  if (isLoading) return null

  return (
    // <PageLayout center>
    //   <TelegramBackButton
    //     onClick={() => appNavigate({ path: ROUTES_NAME.MAIN })}
    //   />
    //   <TelegramMainButton
    //     text="Next"
    //     onClick={() => {
    //       appNavigate({
    //         path: ROUTES_NAME.CHAT,
    //         params: { chatSlug: 'test' },
    //       })
    //     }}
    //   />
    //   <StickerPlayer lottie={confettiLottie} />
    //   <Title
    //     weight="1"
    //     plain
    //     level="1"
    //     className={cn(commonStyles.textCenter, commonStyles.mt16)}
    //   >
    //     Added.
    //     <br />
    //     Now, Configure It!
    //   </Title>
    //   <Text className={cn(commonStyles.textCenter, commonStyles.mt12)}>
    //     Great! Your group is now connected to Gateway. Now it’s time to set
    //     access conditions.
    //   </Text>
    // </PageLayout>
    <PageLayout center>
      <TelegramBackButton onClick={navigateToMainPage} />
      <TelegramMainButton text="Next" onClick={navigateToChat} />
      <StickerPlayer lottie={confettiLottie} />
      <Block margin="top" marginValue={16}>
        <Text type="title" align="center" weight="bold">
          Added.
          <br />
          Now, Configure It!
        </Text>
      </Block>
      <Block margin="top" marginValue={12}>
        <Text type="text" align="center">
          Great! Your group is now connected to Gateway. Now it's time to set
          access conditions.
        </Text>
      </Block>
    </PageLayout>
  )
}
