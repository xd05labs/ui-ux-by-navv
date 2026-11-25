FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
RUN mkdir -p /data && chown appuser:appuser /data
USER appuser
ENV APP_DATABASE=/data/app.sqlite3
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python healthcheck.py
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "app:application"]
