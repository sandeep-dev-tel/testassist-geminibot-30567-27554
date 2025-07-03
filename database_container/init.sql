-- Database initialization script for chatbot app

-- Users table (supports authentication if enabled)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(256), -- SHA/BCrypt etc. Leave NULL for unauthed mode
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table (one per chat session)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table (chat messages between user/bot)
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    sender VARCHAR(16) NOT NULL, -- 'user' or 'bot'
    content TEXT NOT NULL,
    gemini_response JSONB, -- store Gemini response if needed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_msg_convo ON messages(conversation_id);
