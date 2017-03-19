#!/bin/sh
/usr/local/bin/docker rmi -f centos:dev
/usr/local/bin/docker build -t centos:dev .
