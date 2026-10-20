# PiPerch

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=3776AB)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white&labelColor=4FC08D)](https://vuejs.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL_v3-blue.svg?style=flat-square)](https://github.com/fishyy119/PiPerch/blob/master/LICENSE)

## 使用

```shell
pip install piperch
piperch serve
```

### 开发模式

```shell
# 依赖安装
pip install --group dev -e .
corepack enable pnpm
pnpm install --frozen-lockfile

# 终端一：启动后端程序
piperch serve

# 终端二：启动前端开发服务器
pnpm dev
```

## 致谢

感谢以下项目所提供的界面设计灵感、接口实现参考与标签翻译数据：

- [Pixiv_Tag-Chinese-English-Translation-Table](https://github.com/ffdkj/Pixiv_Tag-Chinese-English-Translation-Table)
- [PixivDownloader](https://github.com/Sywyar/PixivDownloader)
- [PixivBiu](https://github.com/txperl/PixivBiu)
