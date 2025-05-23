import { Icon, ListItem, Text, useToast } from '@components'
import { useAppNavigation } from '@hooks'
import { ROUTES_NAME } from '@routes'
import { toUserFriendlyAddress, useTonConnectUI } from '@tonconnect/ui-react'
import { collapseAddress } from '@utils'
import { useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { v4 as uuidv4 } from 'uuid'

import {
  useChat,
  useChatActions,
  useUser,
  useUserActions,
  WalletData,
} from '@store'

export const WalletCondition = () => {
  const { appNavigate } = useAppNavigation()
  const params = useParams<{ clientChatSlug: string }>()

  const chatSlugParam = params.clientChatSlug || ''

  const { showToast } = useToast()

  const { user } = useUser()

  const { chatWallet } = useChat()
  const { fetchUserChatAction } = useChatActions()
  const { connectWalletAction, completeChatTaskAction } = useUserActions()

  const searchParams = new URLSearchParams(window.location.search)
  const connectWalletQuery = searchParams.get('connectWallet')

  const [tonConnectUI] = useTonConnectUI()

  const processedWallets = useRef(new Set<string>())

  const fetchUserChat = async () => {
    try {
      await fetchUserChatAction(chatSlugParam)
    } catch (error) {
      console.error(error)
    }
  }

  const handleCompleteTask = async (taskId: string) => {
    try {
      await completeChatTaskAction(taskId)
      await fetchUserChat()
    } catch (error) {
      console.error(error)
    }
  }

  const handleConnectWallet = async (walletData: WalletData) => {
    if (!chatSlugParam) return
    let taskId = null
    try {
      taskId = await connectWalletAction(chatSlugParam, walletData)

      showToast({
        message: 'New wallet connected',
        type: 'success',
      })
    } catch (error) {
      console.error(error)
      showToast({
        message: 'Failed to connect wallet',
        type: 'error',
      })
    }

    return taskId
  }

  const handleWalletDisconnect = () => {
    try {
      tonConnectUI.disconnect()
    } catch (error) {
      console.error(error)
    }
  }

  const handleOpenWalletConnect = () => {
    handleWalletDisconnect()

    const payload = uuidv4()

    tonConnectUI.setConnectRequestParameters({
      state: 'ready',
      value: { tonProof: payload },
    })

    tonConnectUI.openModal()
  }

  useEffect(() => {
    tonConnectUI.onStatusChange(async (wallet) => {
      if (
        wallet?.connectItems?.tonProof &&
        'proof' in wallet.connectItems.tonProof &&
        !processedWallets.current.has(wallet.account.address)
      ) {
        processedWallets.current.add(wallet.account.address)

        const data = {
          tonProof: wallet.connectItems.tonProof.proof,
          walletAddress: wallet.account.address,
          publicKey: wallet.account.publicKey || '',
        }
        const taskId = await handleConnectWallet(data)
        if (taskId) {
          await handleCompleteTask(taskId)
        }

        await fetchUserChat()
      }
    })
  }, [tonConnectUI])

  useEffect(() => {
    return () => {
      processedWallets.current.clear()
    }
  }, [])

  useEffect(() => {
    if (connectWalletQuery) {
      appNavigate({
        path: ROUTES_NAME.CLIENT_TASKS,
        params: { clientChatSlug: chatSlugParam },
        queryParams: {},
      })
      handleOpenWalletConnect()
    }
  }, [connectWalletQuery])

  const handleWalletsList = () => {
    if (user?.wallets.length) {
      appNavigate({
        path: ROUTES_NAME.CLIENT_WALLETS_LIST,
        params: { clientChatSlug: chatSlugParam },
      })
      return
    }

    handleOpenWalletConnect()
  }

  if (!chatWallet) {
    return (
      <ListItem
        chevron
        onClick={handleWalletsList}
        before={<Icon name="cross" size={24} />}
        text={
          <Text type="text" color="primary">
            Connect Wallet
          </Text>
        }
      />
    )
  }

  const navigateToConnectedWalletPage = () => {
    appNavigate({
      path: ROUTES_NAME.CLIENT_CONNECTED_WALLET,
      params: { clientChatSlug: chatSlugParam },
    })
  }

  const userFriendlyAddress = toUserFriendlyAddress(chatWallet)
  const collapsedAddress = collapseAddress(userFriendlyAddress, 4)

  return (
    <ListItem
      chevron
      onClick={navigateToConnectedWalletPage}
      before={<Icon name="check" size={24} />}
      after={
        <Text type="text" color="tertiary">
          {collapsedAddress}
        </Text>
      }
      text={
        <Text type="text" color="primary">
          Connect Wallet
        </Text>
      }
    />
  )
}
