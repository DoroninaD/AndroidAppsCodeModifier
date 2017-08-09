#!/bin/bash
echo 'start unpacking'
echo $1
java -jar apktool.jar d -f -r -s $1
echo 'unpacking done'
echo 'prepare folder'
FILES=${1%.apk}/lib/armeabi-v7a/*.so

echo ${1%.apk}/lib/armeabi-v7a

echo $path

for f in $FILES

do 
  
arm-none-eabi-objdump -d -m arm -M reg-names-std $f > ${f%.so}.txt
mv $f ${f%.so}_old.so

done
