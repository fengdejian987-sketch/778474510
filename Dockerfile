# 多阶段构建
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS base

# 基础湖段
FROM base AS builder

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 生产段
FROM base AS runtime

WORKDIR /app

# 仅嫩贸 Python 运行时
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制 pip 依赖
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY . .

# 创建作业用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 创建必要目录
RUN mkdir -p /app/logs /app/models

# 创建数据库
# RUN python scripts/init_db.py

# 挂载点
VOLUME ["/app/logs", "/app/models", "/app/data"]

# 暴露端口
EXPOSE 8000 5432

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 启劫BAPI服务
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
