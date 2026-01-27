"""Change message_id to String and ensure node_label exists

Revision ID: 002_vector_id_to_string
Revises: 001_create_omega_vectors_1024
Create Date: 2025-12-23

Purpose:
- Change message_id from BigInteger to String(128) to support Neo4j 5 elementId (strings).
- Ensure node_label column exists (suspected missing from migrations but present in code).
- Add unique constraint on (message_id, node_label) to support idempotent ON CONFLICT inserts.
"""

from alembic import op
import sqlalchemy as sa

revision = "002_vector_id_to_string"
down_revision = "001_create_omega_vectors_1024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()

    # 1. Ensure node_label exists
    result = connection.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='omega_vectors_1024' AND column_name='node_label'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "omega_vectors_1024",
            sa.Column(
                "node_label",
                sa.String(64),
                nullable=False,
                server_default="ChatSession",
                comment="Neo4j node label for this embedding",
            ),
        )

    # 2. Change message_id from BigInteger to String
    # We use postgresql_using to cast existing data
    op.alter_column(
        "omega_vectors_1024",
        "message_id",
        existing_type=sa.BigInteger(),
        type_=sa.String(128),
        postgresql_using="message_id::text",
        comment="Neo4j elementId (string) or legacy ID",
    )

    # 3. Ensure unique constraint exists for ON CONFLICT (message_id, node_label)
    result = connection.execute(
        sa.text(
            "SELECT constraint_name FROM information_schema.table_constraints "
            "WHERE table_name='omega_vectors_1024' AND constraint_name='uq_omega_vectors_message_node'"
        )
    )
    if not result.fetchone():
        op.create_unique_constraint(
            "uq_omega_vectors_message_node",
            "omega_vectors_1024",
            ["message_id", "node_label"],
        )


def downgrade() -> None:
    # Note: Downgrade might fail if message_id contains non-numeric strings
    op.drop_constraint(
        "uq_omega_vectors_message_node", "omega_vectors_1024", type_="unique"
    )
    op.alter_column(
        "omega_vectors_1024",
        "message_id",
        existing_type=sa.String(128),
        type_=sa.BigInteger(),
        postgresql_using="message_id::bigint",
    )
    # We leave node_label as it might have been there before
