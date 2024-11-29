[![Build Status](https://travis-ci.org/openearth/delft3d-gt-server.svg?branch=develop)](https://travis-ci.org/openearth/delft3d-gt-server)
[![codecov](https://codecov.io/gh/openearth/delft3d-gt-server/branch/develop/graph/badge.svg)](https://codecov.io/gh/openearth/delft3d-gt-server)



# delft3d-gt-server
Delft3D Geological Tool web application server


## Install
Make sure to have postgres 12 container up and running:
```bash
docker run -e "POSTGRES_DB=djangodb_test" -e "POSTGRES_HOST_AUTH_METHOD=trust" -e "POSTGRES_USER=postgres" -p5432:5432 postgres:12
```

Install delft3d-gt-ui next to this repo and do
```bash
npm install
npm run build
```
so you end up with a `dist` folder

Duplicate `delft3dgtmain/provisionedsettings.sample.py` to remove the `.sample` and edit it to have:

```
DEBUG = True
ALLOWED_HOSTS = ["*"]
STATIC_ROOT = "./static/"
STATIC_URL = "/static/"
STATICFILES_DIRS = ["../delft3d-gt-ui/dist/"]
```

Now you can do:
```bash
pip install -r requirements.txt
./manage.py collectstatic
./manage.py migrate
./manage.py loaddata delft3dgtmain/fixtures/default_users_groups.json
./manage.py loaddata delft3dworker/fixtures/default_template.json
```

## Run
```bash
./manage.py createsuperuser
./manage.py runserver 0.0.0.0:8000
```


