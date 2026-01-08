# Build an image that can do training and inference in SageMaker
# This is a Python 3 image that uses the nginx, gunicorn, flask stack
# for serving inferences in a stable way.

FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

MAINTAINER Amazon AI <sage-learner@amazon.com>

RUN apt-get -y update && apt-get install -y --no-install-recommends \
    wget \
    python3 \
    nginx \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Here we get all python packages.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set some environment variables. PYTHONUNBUFFERED keeps Python from buffering our standard
# output stream, which means that logs can be delivered to the user quickly. PYTHONDONTWRITEBYTECODE
# keeps Python from writing the .pyc files which are unnecessary in this case. We also update
# PATH so that the train and serve programs are found when the container is invoked.

ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"

# Set up the program in the image
COPY . /opt/program
WORKDIR /opt/program

# Make sure the serving script is executable
RUN chmod +x /opt/program/serve
