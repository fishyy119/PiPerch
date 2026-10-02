# PiPerch

## 使用

### 环境安装

```shell
pip install --group dev -e .

cd frontend
corepack enable pnpm
pnpm install --frozen-lockfile
```

### 开发模式运行

```shell
# 终端一
piperch serve

# 终端二：启动开发服务器后，在 http://127.0.0.1:5173 访问
cd frontend
pnpm dev
```

### 后端托管运行

提前构建页面后，后端直接在 <http://127.0.0.1:9303> 托管页面

```shell
pnpm --dir frontend build
piperch serve
```
