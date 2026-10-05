FROM alpine:3.23
RUN apk add --no-cache asterisk python3 py3-pip \
    && python3 -m venv /opt/venv
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
COPY app /app
LABEL org.opencontainers.image.title="Kiosk Satellite SIP Gateway" \
      org.opencontainers.image.source="https://github.com/Eibelucas/Kiosk-Satellite-SIP" \
      org.opencontainers.image.licenses="Apache-2.0"
WORKDIR /app
ENV PYTHONUNBUFFERED=1
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
  CMD asterisk -rx 'core show uptime' >/dev/null || exit 1
CMD ["/opt/venv/bin/python", "/app/run.py"]
