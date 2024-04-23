# martech-model

## 介绍
一个基于stable video diffusion的图生视频服务，由于任务运行时间较长，且GPU资源运算时没法满足多请求同时占用，这里考虑使用队列来做任务管理
- fastapi 服务
- celery + redis + flower 队列和任务管理


## 部署（单机单卡GPU）

### 安装 linux 的一些包
```bash
## for image and video processing
sudo apt-get install ffmpeg libsm6 libxext6  -y
```

### 安装 miniconda 来管理python环境
```bash
# 如果本地没有，先下载
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O <output_dir>/miniconda.sh

# 运行之后，重开 terminal
bash <output_dir>/miniconda.sh
```


### 安装和运行 redis
这里 redis 跑在本地
```bash
sudo apt-get update
sudo apt-get install redis-server

## 启动 redis-server
## 加密码
sudo vi /etc/redis/redis.conf
## 找到 `requirepass` 修改
## 如果需要手动重启redis
ps aux | grep redis-server
kill -9 <pid>
sudo redis-server /etc/redis/redis.conf
```

### HF 下载模型（大概几个小时）
- stabilityai/stable-video-diffusion-img2vid-xt
```bash

#1.安装依赖
pip install -U huggingface_hub
#2.设置环境变量
export HF_ENDPOINT=https://hf-mirror.com
#3.下载,使用--local-dir-use-symlinks False禁掉软连接，local-dir就是最终下载的路径，而不是链接到.cache/huggingface
huggingface-cli download --resume-download <model_name> --local-dir <local_dir> --local-dir-use-symlinks False

# 帮助说明
huggingface-cli download --help
```
### 拉代码
```bash
mkdir code
cd code
git clone https://github.com/jiniuniu/martech-model.git 
cd martech-model/
```


### 安装环境
```bash
conda create -n svd_env python=3.11
source activate svd_env

# 如果机器重启，把 miniconda3 目录到持久化存储到网盘
pip install -r requirements.txt
```

### 启动
```bash
# 修改 .env
cp .env.example .env

# 启动脚本
./run.sh
```
