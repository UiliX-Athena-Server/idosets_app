# 💪 I Do Sets

[https://idosets.app](https://idosets.app)

A workout webapp that is focused towards doing sets.

![screenshot-readme.png](_assets%2Fscreenshot-readme.png)

## Stack 🥞

- [Flask](https://flask.palletsprojects.com/)
- [SolidJS 2](https://www.solidjs.com/)
- [TailwindCSS](https://tailwindcss.com/)
- [SQLite](https://www.sqlite.org/index.html)
- [Docker](https://www.docker.com/)

## Development 🛠️

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/) and Node.js 22.12+.

```bash
cp .env.needed .env          # then fill in the values
uv sync
(cd frontend && npm install)
uv run flask --app app init-db
uv run qwe dev               # Flask on :5001, Vite on http://127.0.0.1:5002
```

Set `EMAIL_DEV_MODE=1` to print login emails to the console instead of sending them.
Emails are sent with [notifyvia.email](https://pypi.org/project/notifyvia-email/)
and are rate limited to 5 a day per IP address.

```bash
uv run pytest                # backend tests
uv run qwe build             # build the frontend into app/vite (commit the result)
```

## Upgrading from 1.x 🗄️

Version 2 uses a new database file, `instance/idosets.sqlite`. Nothing needs to
be run by hand: when the app starts and finds the old `instance/database.sqlite`
(and the new database is missing or empty) it copies the data across, checks it,
and then deletes the old file. Under gunicorn this happens once in the master
process before the workers start (`on_starting` in `configs/gunicorn.conf.py`);
a lock file (`instance/.startup.lock`) stops processes from doing it twice.

IDs are kept, so existing login links keep working. While copying it removes
duplicate set logs, rows left behind by deleted accounts/exercises/sets, gaps in
set ordering and wrong workout durations. If the new database already has data,
the old file is left alone and a warning is logged.

To migrate another file by hand (this never deletes it):

```bash
uv run flask --app app migrate-db --old path/to/old.sqlite
```

## License 📜

idosets.app © 2024 by David Carmichael is licensed under CC BY-NC-ND 4.0.
To view a copy of this license, visit [this link.](https://creativecommons.org/licenses/by-nc-nd/4.0/)

![](https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1)
![](https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1)
![](https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1)
![](https://mirrors.creativecommons.org/presskit/icons/nd.svg?ref=chooser-v1)
