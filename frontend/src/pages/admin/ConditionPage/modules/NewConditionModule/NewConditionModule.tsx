import {
  AppSelect,
  TelegramMainButton,
  useToast,
  Text,
  Block,
  ListItem,
} from '@components'
import { useAppNavigation } from '@hooks'
import { ROUTES_NAME } from '@routes'
import { removeEmptyFields } from '@utils'
import { useCallback, useEffect, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'

import { Condition, ConditionType, useConditionActions } from '@store'

import { ConditionComponentProps } from '../../components/types'
import { CONDITION_COMPONENTS, CONDITION_TYPES } from '../../constants'

export const NewConditionModule = () => {
  const { appNavigate } = useAppNavigation()
  const params = useParams<{
    chatSlug: string
    conditionType: string
  }>()

  const [isCreating, setIsCreating] = useState(false)

  const chatSlugParam = params.chatSlug || ''
  const conditionTypeParam = params.conditionType || ''

  const location = useLocation()
  const groupId = location.state?.groupId

  const [conditionState, setConditionState] = useState<Partial<Condition>>({
    type: 'jetton',
  })

  const { createConditionAction, resetPrefetchedConditionDataAction } =
    useConditionActions()

  const { showToast } = useToast()

  useEffect(() => {
    if (conditionTypeParam) {
      handleChangeType(conditionTypeParam)
    }
  }, [conditionTypeParam])

  const Component =
    CONDITION_COMPONENTS[
      conditionState.type as keyof typeof CONDITION_COMPONENTS
    ]

  const navigateToChatPage = useCallback(() => {
    appNavigate({
      path: ROUTES_NAME.CHAT,
      params: { chatSlug: chatSlugParam },
    })
  }, [appNavigate, chatSlugParam])

  const handleChangeCondition = (
    key: keyof Condition,
    value?: string | number | number[] | undefined | boolean | null
  ) => {
    setConditionState((prev) => ({
      ...prev,
      [key]: value,
      groupId,
    }))
  }

  const handleCreateCondition = async () => {
    setIsCreating(true)
    try {
      const data = removeEmptyFields(conditionState)
      await createConditionAction({
        type: conditionState.type as ConditionType,
        chatSlug: chatSlugParam,
        data,
      })
      navigateToChatPage()
      showToast({
        message: 'Condition created successfully',
        type: 'success',
      })
    } catch (error) {
      console.error(error)
      if (error instanceof Error) {
        showToast({
          message: error.message,
          type: 'error',
        })
        return
      }

      showToast({
        message: 'Failed to create condition',
        type: 'error',
      })
    } finally {
      setIsCreating(false)
    }
  }

  const handleChangeType = (value: string) => {
    resetPrefetchedConditionDataAction()
    handleChangeCondition('type', value)
    appNavigate({
      path: ROUTES_NAME.CHAT_NEW_CONDITION,
      params: {
        conditionType: value,
        chatSlug: chatSlugParam,
      },
    })
  }

  const setInitialState = (value: Partial<Condition>) => {
    setConditionState(value)
  }

  const payload: ConditionComponentProps = {
    isNewCondition: true,
    handleChangeCondition,
    conditionState,
    setInitialState,
  }

  return (
    <>
      <TelegramMainButton
        text="Add Condition"
        onClick={handleCreateCondition}
        loading={isCreating}
        disabled={isCreating}
      />
      <Block margin="top" marginValue={32}>
        <Text type="title" weight="bold" align="center">
          Add Condition
        </Text>
      </Block>
      <Block margin="top" marginValue={44}>
        <ListItem
          text="Choose type"
          after={
            <AppSelect
              onChange={(value) => handleChangeType(value)}
              options={CONDITION_TYPES}
              value={conditionState.type}
            />
          }
        />
      </Block>
      {Component && <Component {...payload} />}
    </>
  )
}
