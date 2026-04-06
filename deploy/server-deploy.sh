#!/bin/bash
# 服务器端拉取镜像并启动
# 在 AI-Step 目录执行：bash deploy/server-deploy.sh

set -e

REGISTRY="registry.cn-hangzhou.aliyuncs.com/liangjiang-tools/liangjiang-tools"
VERSION=${1:-latest}

echo ">>> 登录阿里云镜像仓库..."
docker login registry.cn-hangzhou.aliyuncs.com

echo ">>> 拉取镜像..."
docker pull ${REGISTRY}:backend-${VERSION}
docker pull ${REGISTRY}:frontend-${VERSION}

# 更新 compose 文件中的版本号
sed -i "s|:backend-.*|:backend-${VERSION}|g" deploy/docker-compose.prod.yml
sed -i "s|:frontend-.*|:frontend-${VERSION}|g" deploy/docker-compose.prod.yml

echo ">>> 重启服务..."
docker compose -f deploy/docker-compose.prod.yml down
docker compose -f deploy/docker-compose.prod.yml up -d

echo ">>> 部署完成！"
docker compose -f deploy/docker-compose.prod.yml ps
