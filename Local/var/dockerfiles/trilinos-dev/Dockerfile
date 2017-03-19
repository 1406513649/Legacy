# build docker container using
#   docker build -t trilinos-dev
# run the container using
#   docker run -i -t trilinos-dev /bin/bash
#
FROM sems-env:latest

ARG username=trilinos
RUN adduser $username
WORKDIR /home/$username

# Copy and unpack trilinos source
COPY trilinos.tar.gz /home/$username
RUN tar xzf trilinos.tar.gz
RUN mv Source source

RUN mkdir /home/$username/build
RUN echo '#!/bin/sh' > /home/$username/build/checkin-test-sems.sh
RUN echo 'TRILINOS_DIR=/home/$username/source' >> /home/$username/build/checkin-test-sems.sh
RUN echo 'TRILINOS_DIR=\$TRILINOS_DIR \$TRILINOS_DIR/cmake/std/sems/checkin-test-sems.sh $@' >> /home/$username/build/checkin-test-sems.sh
RUN chmod +x /home/$username/build/checkin-test-sems.sh

RUN chown -R $username: /home/$username
USER $username
