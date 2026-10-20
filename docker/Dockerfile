# ID-Document-Liveness-Detection-Docker
# Before build: download the runtime zip from GitHub Releases into ./lib/cpu
FROM --platform=linux/amd64 python:3.12-slim-trixie

RUN apt-get update -y && apt-get install -y --no-install-recommends \
        libpcsclite1 psmisc curl util-linux e2fsprogs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root/documentlivenesssdk

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY sdk ./sdk
COPY server ./server
COPY run_server.py ./
COPY lib ./lib/

ENV LD_LIBRARY_PATH=/root/documentlivenesssdk/lib/cpu
ENV PORT=14107
RUN test -f ./lib/cpu/libDocLivenessSDK.so \
    && test -f ./lib/cpu/libdcrliveness.so \
    && test -f ./lib/cpu/document.xdb \
    && test -f ./server/port_guard.py

CMD ["python3", "run_server.py"]
EXPOSE 14107
