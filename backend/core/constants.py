from pathlib import Path

POOL_TIMEOUT = 30
DEFAULT_CONNECT_TIMEOUT = 180
DEFAULT_EXPIRY_TIMEOUT_MINUTES = 30

DEFAULT_WALLET_BALANCE = 0

DEFAULT_WALLET_TRACK_EXPIRATION = 60 * 60 * 24 * 365 * 10  # 10 years

ASYNC_TASK_REDIS_PREFIX = "atask"

# Performance
DEFAULT_BATCH_PROCESSING_SIZE = 5_000

# Privileges required for admin to manage the chat in the bot
REQUIRED_ADMIN_PRIVILEGES = ["add_admins"]
# Privileges required for a bot user to manage the chat
REQUIRED_BOT_PRIVILEGES = ["invite_users", "ban_users"]

# ------------------ Redis --------------------
UPDATED_WALLETS_SET_NAME = "updated_wallets"
DISCONNECTED_WALLETS_SET_NAME = "disconnected_wallets"
UPDATED_STICKERS_USER_IDS = "updated_stickers_user_ids"
CELERY_WALLET_FETCH_QUEUE_NAME = "wallet-fetch-queue"
CELERY_STICKER_FETCH_QUEUE_NAME = "sticker-fetch-queue"
CELERY_NOTICED_WALLETS_UPLOAD_QUEUE_NAME = "noticed-wallets-upload-queue"
CELERY_SYSTEM_QUEUE_NAME = "system-queue"

# ----------------- Paths ---------------------
PACKAGE_ROOT = Path(__file__).parent
PROJECT_ROOT = PACKAGE_ROOT.parent

# ---------------- Static files ----------------
STATIC_PATH = PACKAGE_ROOT / "static"
CERTS_PATH = PACKAGE_ROOT.parent.parent / "config" / "certs"
# ----------------- Requests -----------------
REQUEST_TIMEOUT = 30
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
PROMOTE_JETTON_TEMPLATE = (
    "https://app.ston.fi/swap?chartVisible=false&ft=TON&tt={jetton_master_address}"
)
PROMOTE_NFT_COLLECTION_TEMPLATE = "https://getgems.io/collection/{collection_address}"
PROMOTE_STICKER_COLLECTION_TEMPLATE = (
    "https://t.me/sticker_bot/?startapp=cid_{collection_id}"
)
BUY_TONCOIN_URL = "https://t.me/wallet/start"
BUY_PREMIUM_URL = "https://t.me/PremiumBot"
