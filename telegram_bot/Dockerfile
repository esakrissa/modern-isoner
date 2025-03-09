FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use PORT environment variable with default to 8080
ENV PORT=8080

# Use the PORT environment variable in the CMD
# The bot.py file should be updated to listen on the PORT environment variable
CMD ["sh", "-c", "python bot.py"] 