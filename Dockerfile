FROM yegle/fava
FROM debian:bullseye-slim as build_env
RUN apt-get update
RUN apt-get install -y python3-pip git
RUN pip3 install git+https://github.com/patriq/beantools
