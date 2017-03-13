#!/bin/bash

curl -O https://fastdl.mongodb.org/osx/mongodb-osx-x86_64-3.4.2.tgz
tar -zxvf mongodb-osx-x86_64-3.4.2.tgz
mkdir -p mongodb
mv mongodb-osx-x86_64-3.4.2/* mongodb
rm mongodb-osx-x86_64-3.4.2.tgz
rm -rf mongodb-osx-x86_64-3.4.2
