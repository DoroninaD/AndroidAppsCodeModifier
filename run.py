from os import listdir
from os.path import isfile, join
import main_insert_border_regs, sys

#path = 'data/com.instagram.android/lib/armeabi-v7a/'
#path = 'data/noassertTel/lib/armeabi-v7a/'
path = 'apps/telegram/lib/armeabi-v7a/'

#path = sys.argv[1] #путь к папке todo uncomment
start_group = sys.argv[2] if len(sys.argv)>2 else 0
end_group = sys.argv[3] if len(sys.argv)>3 else -1 #todo LAST ELEMENT!!!

#todo debug only
#start_group = 2314
#end_group = 2315

files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('_old.so')]
for file in files:
    print (file[:-7])
    main_insert_border_regs.run(join(path, file)[:-7], int(start_group), int(end_group))