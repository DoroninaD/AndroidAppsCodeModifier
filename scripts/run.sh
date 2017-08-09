#!/bin/bash
# -*- coding: utf-8 -*-java -jar apktool.jar b -o $2 ${1%.apk}
# 1 = apk name, 2 = new apk name
/usr/bin/python3.5 ../run.py ${1%.apk}/lib/armeabi-v7a/ $3 $4

java -jar apktool.jar b -o $2 ${1%.apk}
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.keystore -storepass 111111 $2 alias_name
adb shell pm uninstall -k org.telegram.messenger.beta
adb install $2
spd-say done

