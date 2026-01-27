-- Initialize PostgreSQL database with pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE product_to_code TO "user";
