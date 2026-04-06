#!/bin/bash
# 本地构建镜像并推送到阿里云镜像仓库
# 在项目根目录执行：bash deploy/build-push.sh

set -e

REGISTRY="registry.cn-hangzhou.aliyuncs.com/liangjiang-tools/liangjiang-tools"
VERSION=${1:-latest}

echo ">>> 登录阿里云镜像仓库..."
docker login registry.cn-hangzhou.aliyuncs.com

echo ">>> 构建后端镜像: ${REGISTRY}:backend-${VERSION}"
docker build -t ${REGISTRY}:backend-${VERSION} -f backend/Dockerfile .

echo ">>> 构建前端镜像: ${REGISTRY}:frontend-${VERSION}"
docker build -t ${REGISTRY}:frontend-${VERSION} -f frontend/Dockerfile frontend/

echo ">>> 推送后端镜像..."
docker push ${REGISTRY}:backend-${VERSION}

echo ">>> 推送前端镜像..."
docker push ${REGISTRY}:frontend-${VERSION}

echo ">>> 完成！镜像版本: ${VERSION}"
echo "    后端: ${REGISTRY}:backend-${VERSION}"
echo "    前端: ${REGISTRY}:frontend-${VERSION}"
