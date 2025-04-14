import { Block, Image, List, ListItem, Text } from '@components'
import { useAppNavigation } from '@hooks'
import { ROUTES_NAME } from '@routes'

import { AdminChat } from '@store'

interface ChannelsListProps {
  channels: AdminChat[]
}

export const ChannelsList = ({ channels }: ChannelsListProps) => {
  const { appNavigate } = useAppNavigation()

  const handleClick = (channel: AdminChat) => {
    appNavigate({
      path: ROUTES_NAME.CHAT,
      params: { chatSlug: channel.slug },
    })
  }

  return (
    <Block margin="top" marginValue={24}>
      <List header="Groups & Channels" separatorLeftGap={24}>
        {channels.map((channel) => {
          return (
            <ListItem
              key={channel.id}
              text={
                <Text type="text" weight="medium">
                  {channel.title}
                </Text>
              }
              chevron
              before={
                <Image src={channel.logoPath} size={24} borderRadius={50} />
              }
              onClick={() => handleClick(channel)}
            />
          )
        })}
      </List>
    </Block>
  )
}
