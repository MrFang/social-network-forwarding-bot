BEGIN;

CREATE TABLE channel_to_vk (
    id              SERIAL PRIMARY KEY,
    channel_id      BIGINT NOT NULL, -- id Telegram канала
    vk_access_token TEXT, -- VK токен доступа, может быть NULL, если пользователь ещё не завершил авторизацию
    issued_by       BIGINT NOT NULL, -- id Telegram пользователя создавшего связь
    issued_at       TIMESTAMP NOT NULL DEFAULT NOW() -- Время создания запроса на регистрацию свзязи
);

COMMIT;
