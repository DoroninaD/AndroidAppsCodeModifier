#!/bin/bash

# -*- coding: utf-8 -*-
echo 'start'
echo $1
java -jar apktool.jar d -f -r -s $1
echo 'java done'

FILES=${1%.apk}/lib/armeabi-v7a/*.so

echo ${1%.apk}/lib/armeabi-v7a

echo $path

for f in $FILES

do 
  
arm-none-eabi-objdump -d -m arm -M reg-names-std $f > ${f%.so}.txt
mv $f ${f%.so}_old.so

done



echo 'Unpacked, running security...'
python3 ../run.py ${1%.apk}/lib/armeabi-v7a/
echo 'Security done, packing...'
sudo rm ${1%.apk}/lib/armeabi-v7a/*.txt

sudo rm ${1%.apk}/lib/armeabi-v7a/*_old.so


java -jar apktool.jar b -o $2 ${1%.apk}

jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore $2 alias_name


