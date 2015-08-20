from decouple import config

token = config('TOKEN', default='')
database_url = config('DATABASE_URL', default='file://db.fs')
port = config('PORT', default='8899')
webhook = config('WEBHOOK', default=False)
