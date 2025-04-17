import { Block, Icon, List, ListItem, Text } from '@components'
import { useAppNavigation } from '@hooks'
import { ROUTES_NAME } from '@routes'
import { createConditionName } from '@utils'

import { useChat, Condition } from '@store'

export const ChatConditions = () => {
  const { appNavigate } = useAppNavigation()
  const { chat, rules } = useChat()

  const createCondition = async () => {
    if (!chat?.slug) return
    appNavigate({
      path: ROUTES_NAME.CHAT_NEW_CONDITION,
      params: {
        chatSlug: chat?.slug,
        conditionType: 'jetton',
      },
    })
  }

  const navigateToConditionPage = (rule: Condition) => {
    appNavigate({
      path: ROUTES_NAME.CHAT_CONDITION,
      params: {
        conditionId: rule.id,
        chatSlug: chat?.slug,
        conditionType: rule.type,
      },
    })
  }

  return (
    <Block margin="top" marginValue={24}>
      <List header="Who can Join" separatorLeftGap={16}>
        {rules?.map((rule) => (
          <ListItem
            key={rule.id}
            chevron
            text={createConditionName(rule)}
            onClick={() => navigateToConditionPage(rule)}
          />
        ))}
        <ListItem
          text={
            <Text type="text" color="accent">
              Add Condition
            </Text>
          }
          onClick={createCondition}
          before={<Icon name="plus" size={28} />}
        />
      </List>
    </Block>
  )
}
