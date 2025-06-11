"""emoji logo url

Revision ID: a02acc5ddb6e
Revises: 53b283880538
Create Date: 2025-06-10 19:00:58.556112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a02acc5ddb6e"
down_revision: Union[str, None] = "53b283880538"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_chat_emoji",
        sa.Column("logo_url", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("telegram_chat_emoji", "logo_url")
