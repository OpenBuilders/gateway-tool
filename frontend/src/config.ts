interface Config {
  isDev?: boolean
  isProd?: boolean
  apiHost: string
  botLink: string
  tonConnectManifestUrl: string
  accessToken?: string
  botName: string
}

const devConfig: Config = {
  isDev: true,
  apiHost: 'https://dev-api.gateway.tools.tg',
  botName: 'ggooccttaa_bot',
  botLink: 'https://t.me/ggooccttaa_bot',
  tonConnectManifestUrl: 'https://cdn.joincommunity.xyz/gateway/manifest.json',
  accessToken: import.meta.env.VITE_ACCESS_TOKEN,
}

const prodConfig: Config = {
  isProd: true,
  apiHost: 'https://api.gateway.tools.tg',
  botName: 'gateway_app_bot',
  botLink: 'https://t.me/gateway_app_bot',
  tonConnectManifestUrl: 'https://cdn.joincommunity.xyz/gateway/manifest.json',
}

let config

switch (import.meta.env.MODE) {
  case 'production':
    config = { ...prodConfig }
    break
  default:
    config = { ...devConfig }
}

export default config as Config
