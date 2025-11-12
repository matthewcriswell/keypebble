# Start from a lightweight base with Python installed
FROM python:3.11

# Set up working directory
WORKDIR /app

# Copy the built wheel into the image
# (assuming you've already run `python -m build` in the repo root)
COPY dist/*.whl /tmp/

# Install the package wheel
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

# Optionally, copy non-package files if your app expects them (like config or templates)
# COPY conf/ ./conf/
COPY examples/ ./examples/

# Set default environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port (if applicable)
EXPOSE 8080

# Define default entrypoint or command
CMD ["keypebble"]
