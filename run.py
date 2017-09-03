from os import listdir
from os.path import isfile, join
import main_insert_border_regs, sys, colored

#path = 'data/com.instagram.android/lib/armeabi-v7a/'
#path = 'data/noassertTel/lib/armeabi-v7a/'
#path = 'apps/telegram/lib/armeabi-v7a/'
#harded_path = 'apps/app-debug/lib/armeabi-v7a/'
harded_path = 'apps/test2/lib/armeabi-v7a/'
DEBUG=1
path = sys.argv[1] if len(sys.argv) > 1 else harded_path
start_group = sys.argv[2] if len(sys.argv)>2 else 0
end_group = sys.argv[3] if len(sys.argv)>3 else -1 #todo LAST ELEMENT!!!

#todo debug only
#start_group = 0
#end_group = 1000
#2314

files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('_old.so')]
for file in files:
    colored.printColored (file[:-7], colored.HEADER)
    main_insert_border_regs.run(join(path, file)[:-7], int(start_group), int(end_group), DEBUG)