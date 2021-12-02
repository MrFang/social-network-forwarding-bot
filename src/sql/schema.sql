BEGIN;

-- Связь телеграм канал -- вк страница
CREATE TABLE channel_to_vk (
    id              SERIAL PRIMARY KEY,
    channel_id      BIGINT NOT NULL UNIQUE, -- id Telegram канала
    vk_access_token TEXT, -- VK токен доступа, может быть NULL, если пользователь ещё не завершил авторизацию
    issued_by       BIGINT NOT NULL, -- id Telegram пользователя создавшего связь
    issued_at       TIMESTAMP NOT NULL DEFAULT NOW() -- Время создания запроса на регистрацию свзязи
);

-- Ещё не отправленные из-за ошибок посты. Пока умеем обрабатывать только текстовые
CREATE TABLE deferred_posts (
    id         SERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL REFERENCES channel_to_vk(channel_id), -- id Telegram канала
    post_text  TEXT NOT NULL -- Текст поста
);

-- Пользователи, от которых мы ждём повторной ссылки с VK логином
CREATE TABLE pending_logins (
    id        SERIAL PRIMARY KEY,
    user_id   BIGINT NOT NULL UNIQUE -- id Telegrm пользователя
);

COMMIT;
