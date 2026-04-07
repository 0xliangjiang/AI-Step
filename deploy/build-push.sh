#!/bin/bash
# 本地构建镜像并推送到阿里云镜像仓库
# 用法：bash deploy/build-push.sh [版本号]
# 示例：bash deploy/build-push.sh 1.0.0

set -e

REGISTRY="registry.cn-hangzhou.aliyuncs.com/liangjiang-tools/liangjiang-tools"
VERSION=${1:-latest}

# echo ">>> 登录阿里云镜像仓库..."
# docker login --username=良匠爱生活 registry.cn-hangzhou.aliyuncs.com

# -------- 后端 --------
echo ">>> 构建后端镜像..."
docker build -t ai-step-backend:${VERSION} -f backend/Dockerfile .

echo ">>> Tag 后端镜像..."
docker tag ai-step-backend:${VERSION} ${REGISTRY}:backend-${VERSION}

echo ">>> 推送后端镜像..."
docker push ${REGISTRY}:backend-${VERSION}

# -------- 前端 --------
echo ">>> 构建前端镜像..."
docker build -t ai-step-frontend:${VERSION} -f frontend/Dockerfile frontend/

echo ">>> Tag 前端镜像..."
docker tag ai-step-frontend:${VERSION} ${REGISTRY}:frontend-${VERSION}

echo ">>> 推送前端镜像..."
docker push ${REGISTRY}:frontend-${VERSION}

echo ""
echo ">>> 完成！"
echo "    后端: ${REGISTRY}:backend-${VERSION}"
echo "    前端: ${REGISTRY}:frontend-${VERSION}"
