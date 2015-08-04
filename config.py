from decouple import config

token = config('TOKEN', default='')
db_filename = config('DB_FILENAME', default='db.fs')
port = config('PORT', defaul='8899')
