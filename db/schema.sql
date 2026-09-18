
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS chat_conversation (
    id   TEXT PRIMARY KEY,
    user_id  TEXT NOT NULL,

    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_chat_conversation_user_id
    ON chat_conversation(user_id);


CREATE TABLE IF NOT EXISTS chat_messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id    TEXT NOT NULL REFERENCES chat_conversation(id) ON DELETE CASCADE,
    run_id         TEXT NOT NULL,
    thread_id     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('user', 'assistant',  'system')),
    content       TEXT NOT NULL DEFAULT '',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id
    ON chat_messages(conversation_id);


CREATE TABLE IF NOT EXISTS chat_charts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id  UUID NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_chat_charts_message_id
    ON chat_charts(message_id);

