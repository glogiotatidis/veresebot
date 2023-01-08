FROM python:2-onbuild
COPY update.py /usr/local/lib/python2.7/site-packages/telegram/update.py

EXPOSE 80
