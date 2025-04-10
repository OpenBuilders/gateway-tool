import {
  AppSelect,
  Container,
  TelegramBackButton,
  TelegramMainButton,
  PageLayout,
  useToast,
} from '@components'
import { useAppNavigation } from '@hooks'
import { ROUTES_NAME } from '@routes'
import { Cell, Section, Title } from '@telegram-apps/telegram-ui'
import { useParams } from 'react-router-dom'

import {
  Condition,
  ConditionType,
  useCondition,
  useConditionActions,
} from '@store'

import styles from '../../ConditionPage.module.scss'
import { CONDITION_COMPONENTS, CONDITION_TYPES } from '../../constants'

export const NewConditionModule = () => {
  const { appNavigate } = useAppNavigation()
  const params = useParams<{
    chatSlug: string
    conditionType: string
  }>()

  const chatSlugParam = params.chatSlug || ''
  const conditionTypeParam = params.conditionType || ''

  const {
    createConditionAction,
    resetPrefetchedConditionDataAction,
    handleChangeConditionFieldAction,
  } = useConditionActions()
  const { isValid, condition } = useCondition()

  const { showToast } = useToast()

  const Component =
    CONDITION_COMPONENTS[
      conditionTypeParam as keyof typeof CONDITION_COMPONENTS
    ]

  const navigateToChatPage = () => {
    appNavigate({
      path: ROUTES_NAME.CHAT,
      params: { chatSlug: chatSlugParam },
    })
  }

  if (!Component) return null

  const handleCreateCondition = async () => {
    try {
      await createConditionAction({
        type: conditionTypeParam as ConditionType,
        chatSlug: chatSlugParam,
        data: condition as Condition,
      })
      navigateToChatPage()
      showToast({
        message: 'Condition created successfully',
        type: 'success',
      })
    } catch (error) {
      console.error(error)
      showToast({
        message: 'Failed to create condition',
        type: 'error',
      })
    }
  }

  const handleChangeType = (value: string) => {
    resetPrefetchedConditionDataAction()
    handleChangeConditionFieldAction('category', value)
    appNavigate({
      path: ROUTES_NAME.CHAT_NEW_CONDITION,
      params: {
        conditionType: value,
        chatSlug: chatSlugParam,
      },
    })
  }
  return (
    <PageLayout>
      <TelegramBackButton onClick={navigateToChatPage} />
      <TelegramMainButton
        text="Create Condition"
        disabled={!isValid}
        onClick={handleCreateCondition}
      />
      <Title level="1" weight="1" plain className={styles.title}>
        Add condition
      </Title>
      <Container>
        <Section>
          <Cell
            after={
              <AppSelect
                onChange={(value) => handleChangeType(value)}
                options={CONDITION_TYPES}
                value={condition?.category}
              />
            }
          >
            Choose type
          </Cell>
        </Section>
        {Component && <Component isNewCondition />}
      </Container>
    </PageLayout>
  )
}
