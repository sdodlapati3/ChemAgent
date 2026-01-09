FROM continuumio/miniconda3:latest

LABEL maintainer="ChemAgent Team"
LABEL description="ChemAgent - AI-Powered Pharmaceutical Research Assistant"

# Set working directory
WORKDIR /app

# Copy environment file
COPY environment.yml .

# Create conda environment
RUN conda env create -f environment.yml && \
    conda clean -afy

# Activate environment
SHELL ["conda", "run", "-n", "chemagent", "/bin/bash", "-c"]

# Copy application code
COPY . .

# Install package in editable mode
RUN pip install -e ".[dev,llm,web]"

# Expose port for web interface
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CHEMAGENT_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import chemagent; print('OK')" || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "chemagent.web.app"]
