#!/bin/bash

# folder name.apk



sudo rm $1/lib/armeabi-v7a/*.txt
sudo rm $1/lib/armeabi-v7a/*_old.so

java -jar apktool.jar b -o $2 $1

jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore $2  alias_name

