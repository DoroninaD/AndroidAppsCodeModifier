from os import listdir
from os.path import isfile, join
import main_insert_border_regs, sys, colored, config_parser

#path = 'data/com.instagram.android/lib/armeabi-v7a/'
#path = 'data/noassertTel/lib/armeabi-v7a/'
#path = 'apps/telegram/lib/armeabi-v7a/'
#harded_path = 'apps/app-debug/lib/armeabi-v7a/'
harded_path = 'apps/curl/lib/armeabi-v7a/'
DEBUG=1
path = sys.argv[1] if len(sys.argv) > 1 else harded_path
config_path = sys.argv[2] if len(sys.argv)>2 else 'config.ini'
start_group = sys.argv[3] if len(sys.argv)>3 else 0
end_group = sys.argv[4] if len(sys.argv)>4 else sys.maxsize #todo LAST ELEMENT!!!

#todo debug only
# start_group = 387
# end_group = 388 #388
#2314

# 1-путь к либами,2-конфиг, 3-начало, 4-конец



files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('_old.so')]
config = config_parser.ConfigParser(config_path)
for file in files:
    # if file[:-7]=='libcurl':
    #     start_group = 0
    #     #end_group = 387
    #     end_group = -1
    # else:
    #     start_group = 0
    #     end_group = 1


    colored.printColored (file[:-7], colored.HEADER)
    main_insert_border_regs.run(join(path, file)[:-7], int(start_group), int(end_group), DEBUG, config)