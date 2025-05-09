import { create } from 'zustand'

import { Condition } from '../condition'
import { createSelectors } from '../types'
import {
  fetchAdminUserChatsAPI,
  fetchChatAPI,
  fetchUserChatAPI,
  updateChatAPI,
  updateChatVisibilityAPI,
} from './api'
import { AdminChat, ChatInstance } from './types'

interface ChatStore {
  adminChats: AdminChat[] | null
  chat: ChatInstance | null
  rules: Condition[] | null
  chatWallet: string | null
}

interface ChatActions {
  actions: {
    fetchChatAction: (slug: string) => Promise<{
      chat: ChatInstance | null
      rules: Condition[] | null
    }>
    updateChatAction: (slug: string, data: Partial<ChatInstance>) => void
    fetchAdminUserChatsAction: () => Promise<AdminChat[]>
    fetchUserChatAction: (slug: string) => void
    updateChatVisibilityAction: (
      slug: string,
      data: Partial<ChatInstance>
    ) => void
  }
}

const useChatStore = create<ChatStore & ChatActions>((set) => ({
  chat: null,
  rules: null,
  adminChats: null,
  chatWallet: null,
  actions: {
    fetchChatAction: async (slug) => {
      const { data, ok, error } = await fetchChatAPI(slug)

      if (!ok || !data) {
        throw new Error(error || 'Chat not found')
      }

      set({ chat: data?.chat, rules: data?.rules })

      return { chat: data?.chat, rules: data?.rules }
    },
    updateChatAction: async (slug, values) => {
      const { data, ok, error } = await updateChatAPI(slug, values)

      if (!ok) {
        throw new Error(error)
      }

      if (!data) {
        throw new Error('Chat data not found')
      }

      set({
        chat: data,
      })
    },
    fetchAdminUserChatsAction: async () => {
      const { data, ok, error } = await fetchAdminUserChatsAPI()

      if (!ok || !data) {
        throw new Error(error)
      }

      set({ adminChats: data })

      return data
    },
    fetchUserChatAction: async (slug) => {
      const { data, ok, error } = await fetchUserChatAPI(slug)

      if (!ok || !data) {
        throw new Error(error)
      }

      set({ chat: data?.chat, rules: data?.rules, chatWallet: data?.wallet })
    },
    updateChatVisibilityAction: async (slug, values) => {
      const { data, ok, error } = await updateChatVisibilityAPI(slug, values)

      if (!ok) {
        throw new Error(error)
      }

      if (!data) {
        throw new Error('Chat data not found')
      }

      set({ chat: data })
    },
  },
}))

export const useChatActions = () => useChatStore((state) => state.actions)

export const useChat = createSelectors(useChatStore)
