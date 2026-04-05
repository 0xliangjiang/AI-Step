FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（ddddocr / Pillow 需要）
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY step_service/requirements.txt ./step_service/requirements.txt
RUN pip install --no-cache-dir -r step_service/requirements.txt

# 复制源码（从项目根目录构建，以便包含 step_brush.py）
COPY step_brush.py ./
COPY step_service/ ./step_service/

WORKDIR /app/step_service

EXPOSE 8001

CMD ["python", "main.py"]
