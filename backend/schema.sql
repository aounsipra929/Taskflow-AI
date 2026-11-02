-- Reference schema (Alembic migration 0001 creates the same structure).
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    full_name       VARCHAR(120) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL DEFAULT 'user',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_users_role CHECK (role IN ('admin', 'user'))
);
CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE tasks (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    priority    VARCHAR(10)  NOT NULL DEFAULT 'medium',
    status      VARCHAR(10)  NOT NULL DEFAULT 'pending',
    due_date    DATE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    user_id     INTEGER      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT ck_tasks_priority CHECK (priority IN ('low', 'medium', 'high')),
    CONSTRAINT ck_tasks_status   CHECK (status IN ('pending', 'completed')),
    CONSTRAINT ck_tasks_title_not_empty CHECK (length(title) > 0)
);
CREATE INDEX ix_tasks_user_id       ON tasks (user_id);
CREATE INDEX ix_tasks_priority      ON tasks (priority);
CREATE INDEX ix_tasks_status        ON tasks (status);
CREATE INDEX ix_tasks_due_date      ON tasks (due_date);
CREATE INDEX ix_tasks_user_status   ON tasks (user_id, status);
CREATE INDEX ix_tasks_user_due_date ON tasks (user_id, due_date);

-- Chatbot Assistant: task changes proposed by the LLM that await user confirmation
CREATE TABLE pending_actions (
    id          VARCHAR(36)  PRIMARY KEY,
    user_id     INTEGER      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    action_type VARCHAR(20)  NOT NULL,
    payload     JSON         NOT NULL,
    summary     TEXT         NOT NULL,
    status      VARCHAR(12)  NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ  NOT NULL
);
CREATE INDEX ix_pending_actions_user_id     ON pending_actions (user_id);
CREATE INDEX ix_pending_actions_user_status ON pending_actions (user_id, status);
