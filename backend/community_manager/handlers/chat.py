import logging

from sqlalchemy.exc import NoResultFound
from telethon import events

from core.actions.authorization import AuthorizationAction
from core.actions.chat import TelegramChatAction
from core.actions.user import UserAction
from core.dtos.chat import TelegramChatDTO
from core.dtos.user import TelegramUserDTO
from core.exceptions.chat import TelegramChatPublicError
from core.services.chat import TelegramChatService
from core.services.chat.user import TelegramChatUserService
from core.services.db import DBService
from core.utils.events import ChatJoinRequestEventBuilder, ChatAdminChangeEventBuilder

logger = logging.getLogger(__name__)


__all__ = [
    "handle_chat_action",
    "handle_join_request",
    "handle_chat_participant_update",
]


async def handle_chat_action(event: events.ChatAction.Event):
    with DBService().db_session() as session:
        telegram_chat_service = TelegramChatService(session)
        if not telegram_chat_service.check_exists(event.chat_id):
            logger.debug(
                "Chat doesn't exist, but bot was not added to the chat: %d. Skipping event...",
                event.chat_id,
            )
            return

        if event.new_photo:
            # Photo was deleted
            if not event.photo:
                telegram_chat_service.clear_logo(chat_id=event.chat_id)
                return

            telegram_chat_action = TelegramChatAction(
                session, telethon_client=event.client
            )
            logo_path = await telegram_chat_action.fetch_and_push_profile_photo(
                event.chat,
                # We definitely know here that the new photo was set - no need to fetch the current value
                current_logo_path=None,
            )
            if logo_path:
                logger.debug(
                    f"Updating logo for chat {event.chat_id!r} with path {logo_path!r}..."
                )
                telegram_chat_service.set_logo(
                    chat_id=event.chat_id, logo_path=logo_path
                )
            else:
                logger.warning(
                    f"Ignoring update for chat {event.chat_id!r} as logo was not downloaded.."
                )
            return

        logger.debug(
            f"Chat action: {event.chat_id=!r} {event.user_id=!r} {event.action_message=!r}",
            extra={"event": event},
        )

        if not any(
            [event.user_joined, event.user_added, event.user_left, event.user_kicked]
        ):
            # To avoid handling other chat actions as they are not supported
            logger.debug(f"Unhandled chat action: {event!r}. Skipping.")
            return

        elif event.action_message:
            # To avoid handling multiple events twice (users are added or removed and the action message is sent)
            # The only message that should be handled is when bot is added to the chat
            logger.debug(f"Chat action message {event!r} is not handled.")
            return

        elif event.user.bot and not event.user.is_self:
            logger.debug(f"Another bot user {event.user.id!r} is not handled.")
            return

        authorization_action = AuthorizationAction(
            session, telethon_client=event.client
        )

        if event.user_joined or event.user_added:
            if event.added_by and event.added_by.is_self:
                # Do not handle actions made by the bot
                logger.debug(
                    f"Action made by the bot {event.added_by.id!r}. Already handled."
                )
                return

            elif event.user.is_self:
                logger.info(
                    f"Bot was added to chat: {event.chat_id=!r}",
                )
                return

            logger.info(
                f"New chat member: {event.chat_id=!r} {event.user.id=!r}",
                extra={"event": event},
            )
            await authorization_action.on_chat_member_in(
                chat_id=event.chat_id,
                user=TelegramUserDTO.from_telethon_user(event.user),
            )

        elif event.user_left or event.user_kicked:
            if event.kicked_by and event.kicked_by.is_self:
                # Do not handle actions made by the bot
                logger.debug(f"Action made by the bot {event.kicked_by.id!r}.")
                return

            if event.user.is_self:
                logger.warning(
                    f"Bot was kicked from chat: {event.chat_id=!r}",
                    extra={"event": event},
                )
                await authorization_action.on_bot_kicked(chat_id=event.chat_id)
                return

            logger.info(
                f"Chat member left/kicked: {event.chat_id=!r} {event.user_id=!r}",
                extra={"event": event},
            )
            await authorization_action.on_chat_member_out(
                chat_id=event.chat_id,
                user=TelegramUserDTO.from_telethon_user(event.user),
            )

        else:
            logger.debug(f"Unhandled chat action: {event!r}")


async def handle_join_request(event: ChatJoinRequestEventBuilder.Event):
    logger.info(
        f"New join request: {event.chat_id=!r} {event.user_id=!r}",
    )
    with DBService().db_session() as session:
        authorization_action = AuthorizationAction(
            session, telethon_client=event.client
        )
        await authorization_action.on_join_request(
            telegram_user_id=event.user_id,
            chat_id=event.chat_id,
            invited_by_bot=event.invited_by_current_user,
            invite_link=event.invite_link,
        )


async def handle_chat_participant_update(
    event: ChatAdminChangeEventBuilder.Event,
) -> None:
    """Does not handle kicks from the chat"""
    # Chat ID received from the event is not prefixed with -100 for channels,
    #  so we need to prefix it if needed
    chat_id = int(
        f"-100{event.original_update.channel_id}"
        if event.original_update.channel_id > 0
        else event.original_update.channel_id
    )
    with DBService().db_session() as session:
        telegram_chat_service = TelegramChatService(session)
        chat: TelegramChatDTO | None = None
        try:
            chat = TelegramChatDTO.from_object(telegram_chat_service.get(chat_id))
        except NoResultFound:
            pass

        if not chat:
            # If bot is able to see that update, it means it was promoted to admins
            #  at some point, so the chat should be created in the database
            if event.is_self and event.sufficient_bot_privileges:
                # Create a new chat if bot privileges are sufficient for this
                logger.info(
                    f"Chat {chat_id!r} doesn't exist, but bot was added with admin rights. Creating..."
                )
                telegram_chat_action = TelegramChatAction(
                    session, telethon_client=event.client
                )
                try:
                    await telegram_chat_action.create(
                        chat_id,
                        sufficient_bot_privileges=event.sufficient_bot_privileges,
                    )
                except TelegramChatPublicError:
                    # Nothing to do if the chat/channel is public
                    return
            else:
                logger.debug(
                    f"Chat {chat_id!r} doesn't exist, but bot was added without admin rights. Skipping."
                )
            return

        # If chat already existed
        logger.debug("Handling chat participant update %s", event)

        # Handling updates for the bot user
        if event.is_self:
            logger.info(
                "The Bot user is managed in the chat %d: %s",
                chat_id,
                event.new_participant,
            )
            if not event.sufficient_bot_privileges:
                if not chat.insufficient_privileges:
                    logger.warning(
                        "Insufficient permissions for the bot in chat %d", chat_id
                    )
                    telegram_chat_service.set_insufficient_privileges(
                        chat_id=chat_id, value=True
                    )
            else:
                if chat.insufficient_privileges:
                    logger.info(
                        "Sufficient permissions for the bot in chat %d", chat_id
                    )
                    telegram_chat_service.set_insufficient_privileges(
                        chat_id=chat_id, value=False
                    )
            return

        # Ignore actions done on other bots
        if (target_telethon_user := event.user) and target_telethon_user.bot:
            logger.debug(f"Bot user {target_telethon_user.id!r} is not handled.")
            return

        user_action = UserAction(session)
        target_user = user_action.get_or_create(
            telegram_user=TelegramUserDTO.from_telethon_user(target_telethon_user)
        )
        telegram_chat_user_service = TelegramChatUserService(db_session=session)

        try:
            target_chat_user = telegram_chat_user_service.get(
                chat_id=chat.id, user_id=target_user.id
            )
        except NoResultFound:
            logger.info(
                f"No chat user found in chat {chat.id!r} for user {target_user.id!r}. Creating..."
            )
            telegram_chat_user_service.create(
                chat_id=chat.id,
                user_id=target_user.id,
                is_admin=event.has_enough_rights,
                # Because it was not added by the bot user
                is_managed=False,
            )
            return

        # Handle admin privileges update on the normal user
        if event.is_demoted or not event.has_enough_rights:
            if target_chat_user.is_admin:
                logger.info("Admin %d demoted in chat %d", target_user.id, chat.id)
                telegram_chat_user_service.demote_admin(
                    chat_id=chat.id, user_id=target_chat_user.user_id
                )
            return

        elif event.has_enough_rights:
            if not target_chat_user.is_admin:
                logger.info("Admin %d promoted in chat %d", target_user.id, chat.id)
                telegram_chat_user_service.promote_admin(
                    chat_id=chat.id,
                    user_id=target_user.id,
                )
            return
