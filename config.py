from decouple import config

token = config('TOKEN', default='')
db_filename = config('DB_FILENAME', default='db.fs')
port = config('PORT', default='8899')
webhook = config('WEBHOOK', default=False)
