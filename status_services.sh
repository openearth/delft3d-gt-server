#! /bin/bash
clear
systemctl status docker -n 3
systemctl status redis -n 3
systemctl status celery -n 3
systemctl status httpd -n 3