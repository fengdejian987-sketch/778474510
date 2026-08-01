---

## 🚀 部署配置（示例已脱敏）

以下示例已移除任何硬编码或示例密码，并改为使用环境变量占位。请在生产环境中使用 GitHub Actions secrets 或云平台的 Secrets/Key Management 来注入真实凭据，并在部署后立即旋转初始凭据。

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 初始化数据库（仅在需要时运行）
# RUN python scripts/init_db.py

# 暴露端口
EXPOSE 8000

# 启动API服务
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml (脱敏示例)
version: '3.8'

services:
  database:
    image: postgres:15
    environment:
      # 使用环境变量注入密码，切勿在仓库中硬编码
      POSTGRES_PASSWORD: ${DB_PASSWORD:-}
      POSTGRES_DB: ${DB_NAME:-formula_db}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api:
    build: .
    depends_on:
      - database
    environment:
      # 建议使用 DATABASE_URL 或独立的 env 变量并在运行时注入
      DATABASE_URL: ${DATABASE_URL:-}
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs

volumes:
  postgres_data:
```

---

我已在本文件中把原来的 docker-compose 示例中的明文 `secret` 替换为环境变量占位 (`${DB_PASSWORD:-}`) 并加入注释提示不要硬编码密码到仓库。
