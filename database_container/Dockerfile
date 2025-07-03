# Database container for chatbot application (PostgreSQL)
FROM postgres:16-alpine

# Set defaults; these can/should be overridden by docker-compose/.env
ENV POSTGRES_DB=chatbotdb
ENV POSTGRES_USER=chatbotuser
ENV POSTGRES_PASSWORD=chatbotpass

# Copy schema initialization to container entrypoint location
COPY init.sql /docker-entrypoint-initdb.d/init.sql

# PostgreSQL will run on the default port 5432
EXPOSE 5432
