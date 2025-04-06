import { ApiService, ApiServiceResponse } from '@services'

import { ConditionJetton, PrefetchJetton } from './types'

// Jettons

export const createConditionJettonApi = async (
  chatSlug: string
): Promise<ApiServiceResponse<ConditionJetton>> => {
  const response = await ApiService.post<ConditionJetton>({
    endpoint: `/admin/chats/${chatSlug}/rules/jettons`,
    data: {
      expected: 88,
      address:
        '0:2f956143c461769579baef2e32cc2d7bc18283f40d20bb03e432cd603ac33ffc',
    },
  })

  return response
}

export const updateConditionJettonApi = async (
  chatSlug: string,
  conditionId: string,
  data: any
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.put<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/jettons/${conditionId}`,
    data,
  })

  return response
}

export const fetchConditionJettonApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.get<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/jettons/${conditionId}`,
  })

  return response
}

export const deleteConditionJettonApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.delete<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/jettons/${conditionId}`,
  })

  return response
}

// NFT Collection

export const createConditionNFTCollectionApi = async (
  chatSlug: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.post<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/nft-collections`,
  })

  return response
}

export const updateConditionNFTCollectionApi = async (
  chatSlug: string,
  conditionId: string,
  data: any
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.put<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/nft-collections/${conditionId}`,
    data,
  })

  return response
}

export const fetchConditionNFTCollectionApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.get<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/nft-collections/${conditionId}`,
  })

  return response
}

export const deleteConditionNFTCollectionApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.delete<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/nft-collections/${conditionId}`,
  })

  return response
}

// Whitelist

export const createConditionWhitelistApi = async (
  chatSlug: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.post<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists`,
  })

  return response
}

export const updateConditionWhitelistApi = async (
  chatSlug: string,
  conditionId: string,
  data: any
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.put<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists/${conditionId}`,
    data,
  })

  return response
}

export const fetchConditionWhitelistApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.get<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists/${conditionId}`,
  })

  return response
}

export const deleteConditionWhitelistApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.delete<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists/${conditionId}`,
  })

  return response
}

// Whitelist External

export const createConditionWhitelistExternalApi = async (
  chatSlug: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.post<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists-external`,
  })

  return response
}

export const updateConditionWhitelistExternalApi = async (
  chatSlug: string,
  conditionId: string,
  data: any
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.put<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists-external/${conditionId}`,
    data,
  })

  return response
}

export const fetchConditionWhitelistExternalApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.get<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists-external/${conditionId}`,
  })

  return response
}

export const deleteConditionWhitelistExternalApi = async (
  chatSlug: string,
  conditionId: string
): Promise<ApiServiceResponse<any>> => {
  const response = await ApiService.delete<any>({
    endpoint: `/admin/chats/${chatSlug}/rules/whitelists-external/${conditionId}`,
  })

  return response
}

// Other

export const fetchJettonsListApi = async (
  address: string
): Promise<ApiServiceResponse<PrefetchJetton>> => {
  const response = await ApiService.get<PrefetchJetton>({
    endpoint: `/admin/resources/prefetch/jettons?address=${address}`,
  })

  return response
}

export const fetchNDTCollectionsApi = async (): Promise<
  ApiServiceResponse<any>
> => {
  const response = await ApiService.get<any>({
    endpoint: `/admin/resources/prefetch/nft-collections`,
  })

  return response
}
