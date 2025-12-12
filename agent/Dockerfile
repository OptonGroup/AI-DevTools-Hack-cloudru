FROM python:3.12

WORKDIR /app

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Install dependencies
RUN uv sync --no-dev

# Expose port
EXPOSE 10000

# Set environment variables
ENV PORT=10000
ENV LOG_LEVEL=INFO
ENV PATH="/app/.venv/bin:$PATH"

# Run the agent (как в lab3)
CMD ["python", "src/start_a2a.py"]







