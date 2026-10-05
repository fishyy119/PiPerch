# PiPerch

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=3776AB)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white&labelColor=4FC08D)](https://vuejs.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg?style=flat-square)](LICENSE)

## 使用

### 环境安装

```shell
pip install --group dev -e .

corepack enable pnpm
pnpm install --frozen-lockfile
```

### 开发模式运行

```shell
# 终端一
piperch serve

# 终端二：启动开发服务器后，在 http://127.0.0.1:5173 访问
pnpm dev
```

### 后端托管运行

提前构建页面后，后端直接在 <http://127.0.0.1:9303> 托管页面

```shell
pnpm build
piperch serve
```

服务始终监听本地回环地址。需要同时允许指定网卡访问时，可追加监听对应的本机 IPv4 地址；
`--host` 可以重复传入：

```shell
piperch serve --host 192.168.1.10
piperch serve --host 192.168.1.10 --host 192.168.50.10
```

## 致谢

感谢以下项目所提供的界面设计灵感、接口实现参考与标签翻译数据：

- [Pixiv_Tag-Chinese-English-Translation-Table](https://github.com/ffdkj/Pixiv_Tag-Chinese-English-Translation-Table)
- [PixivDownloader](https://github.com/Sywyar/PixivDownloader)
- [PixivBiu](https://github.com/txperl/PixivBiu)
