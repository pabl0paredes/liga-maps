# Liga Geo Diaria

Liga de Globle, Flagle y MapTap para el grupo. Cada uno pega su resultado, se detecta el juego solo y la página calcula el día, el podio semanal y el medallero de la temporada.

- `main.py`: servidor FastAPI. Guarda los resultados en Postgres (en Railway) o en un archivo SQLite si corres en local.
- `static/index.html`: la página.
- Para guardar se pide un **PIN del grupo** (una sola vez por celular). Ver la liga no pide nada.

## Subir a Railway

1. Crea un repo en GitHub y sube esta carpeta:
   ```bash
   git init && git add . && git commit -m "Liga Geo Diaria"
   git branch -M main
   git remote add origin https://github.com/<tu-usuario>/liga-geo.git
   git push -u origin main
   ```
2. En Railway: **New Project → Deploy from GitHub repo** y elige `liga-geo`.
3. En el mismo proyecto: **+ Create → Database → PostgreSQL**.
4. En el servicio de la app, pestaña **Variables**, agrega:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (referencia a la base que creaste)
   - `LIGA_PIN` = el PIN que quieras darle al grupo, por ejemplo `4821`
5. Pestaña **Settings → Networking → Generate Domain**. Ese es el link para el grupo.

La tabla se crea sola la primera vez que arranca el servidor.

## Probar en local

```bash
pip install -r requirements.txt
LIGA_PIN=1234 uvicorn main:app --reload
```
Abre http://localhost:8000. Sin `DATABASE_URL` usa `liga.db` (SQLite).

## Cambios frecuentes

- **Jugadores**: la lista está en dos lugares, `PLAYERS` en `main.py` y `PLAYERS` en `static/index.html`. Cambia ambas.
- **Cambiar el PIN**: edita `LIGA_PIN` en Railway. Los celulares con el PIN viejo lo vuelven a pedir al guardar.
- **Corregir un puntaje**: basta con volver a pegar el resultado de ese día; reemplaza al anterior.
- **Borrar un resultado**: `curl -X DELETE https://<tu-dominio>/api/results/<Jugador>/<AAAA-MM-DD>/<globle|flagle|maptap> -H "X-PIN: <pin>"`
- **Respaldo**: `curl https://<tu-dominio>/api/results > respaldo.json`
