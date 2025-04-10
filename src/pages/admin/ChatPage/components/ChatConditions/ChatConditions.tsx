import { Container, Icon } from '@components'
import { useAppNavigation } from '@hooks'
import { ROUTES_NAME } from '@routes'
import commonStyles from '@styles/commonStyles.module.scss'
import { Cell, Link, Navigation, Section } from '@telegram-apps/telegram-ui'
import cn from 'classnames'

import { useChat, ChatRule } from '@store'

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

  const navigateToConditionPage = (rule: ChatRule) => {
    appNavigate({
      path: ROUTES_NAME.CHAT_CONDITION,
      params: {
        conditionId: rule.id,
        chatSlug: chat?.slug,
        conditionType: rule.category,
      },
    })
  }

  return (
    <Container className={cn(commonStyles.mt8, commonStyles.mb24)}>
      <Section header="Who can Join">
        {rules?.map((rule) => (
          <Navigation
            key={`${rule.id}_${rule.title}`}
            className={commonStyles.pr16}
          >
            <Cell onClick={() => navigateToConditionPage(rule)}>
              {rule.title}
            </Cell>
          </Navigation>
        ))}
        <Cell
          Component={Link}
          before={<Icon name="plus" size={28} />}
          onClick={createCondition}
        >
          Add Condition
        </Cell>
      </Section>
    </Container>
  )
}
