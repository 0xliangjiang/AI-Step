# 线上部署说明

## 1. 服务器准备

- 一台 Linux 服务器
- 已安装 Docker 和 Docker Compose
- 一个用于后端接口的域名，例如 `api.example.com`
- 一个用于后台网页的域名，例如 `admin.example.com`
- 已申请 HTTPS 证书
- 一个可访问的 MySQL 实例

## 2. 准备环境变量

复制模板并填写：

```bash
cp .env.example .env
```

重点必填项：

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`
- `AI_PROVIDER`
- `MINIMAX_API_KEY` 或 `GLM_API_KEY`
- `NANRUN_API_KEY`
- `WX_APPID`
- `WX_SECRET`
- `WX_MCH_ID`
- `WX_API_KEY`
- `WX_API_V3_KEY`
- `WX_NOTIFY_URL`
- `PROXY_API_URL`

如果要用微信支付证书，还要准备：

- `WX_CERT_PATH`
- `WX_KEY_PATH`

## 3. 启动服务

在项目根目录执行：

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
```

查看后端日志：

```bash
docker compose logs -f backend
```

查看前端日志：

```bash
docker compose logs -f frontend
```

## 4. Nginx 反向代理

示例配置文件：

- [deploy/nginx/ai-step.conf](/Users/liangjiang/AI-Step/deploy/nginx/ai-step.conf)

把里面的域名改成你自己的：

- `api.example.com` -> 你的后端域名
- `admin.example.com` -> 你的后台域名

部署到服务器：

```bash
sudo mkdir -p /etc/nginx/conf.d
sudo cp deploy/nginx/ai-step.conf /etc/nginx/conf.d/ai-step.conf
sudo nginx -t
sudo systemctl reload nginx
```

如果你用 HTTPS，建议配合 Certbot：

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com -d admin.example.com
```

## 5. 小程序配置

### 5.1 API 域名切换

文件：

- [miniprogram/app.js](/Users/liangjiang/AI-Step/miniprogram/app.js)

你需要把这几个地址改成真实值：

```js
develop: 'http://127.0.0.1:8000',
trial: 'https://api-staging.example.com',
release: 'https://api.example.com'
```

建议：

- `develop` 保留本地地址
- `trial` 指向预发布环境
- `release` 指向正式环境

### 5.2 小程序 AppID

文件：

- [miniprogram/project.config.json](/Users/liangjiang/AI-Step/miniprogram/project.config.json)

把 `appid` 改成你的小程序正式 `AppID`。

注意：这个值当前仓库里无法自动推断，必须填你微信小程序后台的真实值。

## 6. 微信后台配置

### 6.1 微信小程序后台

在微信公众平台配置合法域名：

- request 合法域名
- uploadFile 合法域名
- downloadFile 合法域名
- socket 合法域名

至少加入：

- `https://api.example.com`

### 6.2 微信支付商户平台

确认以下内容一致：

- 小程序 `AppID`
- 商户号 `WX_MCH_ID`
- 支付密钥 `WX_API_KEY`
- 回调地址 `WX_NOTIFY_URL`

支付回调地址示例：

```text
https://api.example.com/api/pay/notify
```

## 7. 常用生产命令

重建并启动：

```bash
docker compose up -d --build
```

停止服务：

```bash
docker compose down
```

重启后端：

```bash
docker compose restart backend
```

重启前端：

```bash
docker compose restart frontend
```

进入后端容器：

```bash
docker compose exec backend sh
```

查看最近日志：

```bash
docker compose logs --tail=200 backend
docker compose logs --tail=200 frontend
```

## 8. 上线前检查

- `.env` 已填写
- MySQL 可连通
- `docker compose ps` 全部正常
- `https://api.example.com/docs` 可访问
- 小程序能成功调用 `/api/user/wxlogin`
- 后台网页可打开
- 微信支付回调地址已配置
- 小程序后台合法域名已配置
