FROM adamrehn/ue4-engine:4.22.0
MAINTAINER Brandon Haynes "bhaynes@cs.washington.edu"

ENV OUTPUT_PATH=/app

ARG CARLA_VERSION=0.9.6
ARG CARLA_REPOSITORY=https://github.com/carla-simulator/carla

ENV CARLA_PATH=/home/ue4/carla
ENV CARLA_EXECUTABLE=$CARLA_PATH/Unreal/CarlaUE4/Saved/StagedBuilds/LinuxNoEditor/CarlaUE4/Binaries/Linux/CarlaUE4-Linux-Shipping

ENV UNREAL_VERSION=4.22
ENV UNREAL_PATH=/home/ue4/UnrealEngine
ENV UE4_ROOT $UNREAL_PATH

ARG VISUALROAD_VERSION=master
ARG VISUALROAD_REPOSITORY=https://github.com/uwdb/visualroad.git
ENV VISUALROAD_PATH=/home/ue4/visualroad

ENV DEBIAN_FRONTEND noninteractive

##############

USER root

# Install apt dependencies
RUN apt-get update
RUN apt-get install \
        -y \
        --no-install-recommends \
      ca-certificates \
      software-properties-common \
      build-essential \
      g++-7 \
      cmake \
      ninja-build \
      libvulkan1 \
      python \
      python-pip \
      python-dev \
      python-setuptools \
      python-wheel \
      python3-dev \
      python3-pip \
      python3-setuptools \
      python3-wheel \
      libpng-dev \
      libtiff5-dev \
      libjpeg-dev \
      libsm6 \
      libxext6 \
      libxrender-dev \
      tzdata \
      sed \
      curl \
      rsync \
      wget \
      unzip \
      autoconf \
      libtool \
      git \
      ffmpeg

# Install clang
RUN apt-get install -y clang-7 lld-7 && \
    update-alternatives --install /usr/bin/clang++ clang++ /usr/lib/llvm-7/bin/clang++ 170 && \
    update-alternatives --install /usr/bin/clang clang /usr/lib/llvm-7/bin/clang 170

##############

USER ue4

# Ensure yaml, opencv
RUN pip2 install --user pyyaml opencv-python==4.0.1.24 psutil & \
    pip3 install --user pyyaml opencv-python==4.0.1.24 psutil

# Build Carla
RUN git clone https://github.com/carla-simulator/carla $CARLA_PATH && \
    cd $CARLA_PATH && \
    git checkout $CARLA_VERSION && \
    ./Update.sh && \
    make package

# Install Carla Python API
RUN pip2 install --user --upgrade --ignore-installed -e $CARLA_PATH/PythonAPI/carla & \
    pip3 install --user --upgrade --ignore-installed -e $CARLA_PATH/PythonAPI/carla

# Install Visual Road
RUN git clone $VISUALROAD_REPOSITORY $VISUALROAD_PATH && \
    cd $VISUALROAD_PATH && \
    git checkout $VISUALROAD_VERSION

WORKDIR /app
