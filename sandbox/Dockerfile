# Use as the source for a custom E2B template; never run cloned code on the API host.
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest==8.4.2 && (id -u user >/dev/null 2>&1 || useradd --create-home user)
RUN mkdir -p /home/user/repo && chown -R user:user /home/user
USER user
WORKDIR /home/user/repo
