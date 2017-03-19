#!/bin/sh
/usr/local/bin/docker rmi -f centos:sems
/usr/local/bin/docker build -t centos:sems .
