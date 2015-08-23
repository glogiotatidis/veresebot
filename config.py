from decouple import Csv, config

token = config('TOKEN', default='')
database_url = config('DATABASE_URL', default='file://db.fs')
port = config('PORT', default='8899')
webhook = config('WEBHOOK', default=False)
administrators = config('ADMINISTRATORS', default='', cast=Csv(int))
