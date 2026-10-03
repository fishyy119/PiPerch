# PiPerch

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=3776AB)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white&labelColor=4FC08D)](https://vuejs.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg?style=flat-square)](LICENSE)

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
