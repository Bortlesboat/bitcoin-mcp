FROM python:3.12-slim

RUN pip install --no-cache-dir bitcoin-mcp

# stdio transport — no ports exposed
ENTRYPOINT ["bitcoin-mcp"]
