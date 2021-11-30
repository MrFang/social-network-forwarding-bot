BEGIN;

CREATE TABLE channel_to_vk (
    id              SERIAL PRIMARY KEY,
    channel_id      BIGINT NOT NULL, -- id Telegram канала
    vk_access_token TEXT NOT NULL, -- VK токен доступа
    issued_by       BIGINT NOT NULL, -- id Telegram пользователя создавшего связь

    UNIQUE (channel_id, vk_access_token)
);

COMMIT;
