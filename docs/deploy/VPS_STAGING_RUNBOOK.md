# VPS staging runbook — Studio Legale Badrane LegalTech

> Procedura concreta per portare lo staging su un VPS Ubuntu 24.04 LTS
> con Docker, HTTPS via Caddy, Postgres in container e backup giornaliero.
>
> Questo runbook NON sostituisce `STAGING_DEPLOY.md`: lo estende con la
> parte "host fisico + reverse proxy + protezione accesso" che lì è
> volutamente fuori scope.
>
> **Non è una guida prod-go-live.** Per il go-live pubblico vedi
> `PRODUCTION_PREFLIGHT.md` (cookie consent, MFA, monitoring, email
> transactional, rate-limit, off-site backup automatizzato).

## 0. Architettura scelta

```
        Internet
            │  HTTPS 443 (Let's Encrypt)
            ▼
   ┌──────────────────────┐
   │ Caddy (host systemd) │ ← basic_auth, security headers, log
   └──────────┬───────────┘
              │ http://127.0.0.1:8000 (loopback only)
   ┌──────────▼───────────┐
   │ web (gunicorn 3 wkr) │ ← container, immagine `badrane-legaltech:staging`
   └──────────┬───────────┘
              │ TCP 5432 (network docker interna)
   ┌──────────▼───────────┐
   │ db (postgres:16)     │ ← container, volume `postgres_data`
   └──────────────────────┘

   Volumi docker:
   - postgres_data       (DB)
   - media_data          (PDF reports + LegalSourceAttachment)
   - staticfiles_data    (collectstatic output)
   - bind: ./legal_data  (PDF G.U. + CSV + exports)
```

**Perché Caddy e non nginx**

- HTTPS automatico (ACME HTTP-01) senza certbot a parte.
- `basic_auth` e `header` direttive in 5 righe.
- Reload zero-downtime (`systemctl reload caddy`).
- Configurazione totale ≈40 righe vs ≈120 di un setup nginx+certbot equivalente.
- Per uno staging single-host la semplicità batte la familiarità nginx.

Se l'ops dello Studio preferisce nginx, le funzionalità sono le stesse:
serve un blocco `server` con `proxy_pass`, `auth_basic`, certbot per TLS,
e `client_max_body_size 20m`. Non lo includo qui: il runbook si concentra
sul percorso più corto.

**Perché Postgres in container, non managed**

- Staging: dati sintetici / approvati di test. La RPO/RTO non giustifica
  il costo di un Postgres managed.
- In prod, valutare Hetzner Managed Postgres / DigitalOcean / Scaleway
  per ridurre superficie ops (vedi `PRODUCTION_PREFLIGHT.md`).

## 1. Prerequisiti VPS

Hardware minimo:
- 2 vCPU, 4 GB RAM, 40 GB SSD (margine per backup + media).
- IPv4 pubblico statico.
- Rete: porte 22, 80, 443 in ingresso aperte.

Software base (Ubuntu 24.04 LTS):
- ssh con chiave pubblica obbligatoria, password disabilitata.
- ufw o iptables: solo 22/80/443.
- DNS A record: `staging.studiolegalebadrane.it` → IP VPS.
  Verifica `dig +short staging.studiolegalebadrane.it` PRIMA di
  configurare Caddy (altrimenti l'ACME challenge fallisce).

## 2. Hardening base e utente deploy

Tutti i comandi come root o via `sudo`.

```bash
# Aggiornamenti
apt update && apt upgrade -y
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades   # accetta default

# Firewall
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Utente non-root per il deploy
adduser --disabled-password --gecos "" deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Disabilita login root via ssh
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

Da qui in avanti tutti i comandi vanno eseguiti come `deploy`.

## 3. Install Docker + Caddy

```bash
# Docker Engine + compose plugin (repo ufficiale)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
# logout/login per applicare il gruppo, oppure:
newgrp docker
docker --version           # >= 24
docker compose version     # >= v2

# Caddy (repo ufficiale)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
caddy version
```

## 4. Clone repo + .env.staging

```bash
sudo mkdir -p /opt/badrane-legaltech
sudo chown deploy:deploy /opt/badrane-legaltech
git clone <repo-url> /opt/badrane-legaltech
cd /opt/badrane-legaltech

cp .env.staging.example .env.staging
chmod 600 .env.staging
```

Edita `.env.staging` (vedi `STAGING_DEPLOY.md §2` per il dettaglio campi).
Punti critici:
- `DJANGO_SECRET_KEY`: 50 caratteri random.
- `DJANGO_ALLOWED_HOSTS=staging.studiolegalebadrane.it`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.studiolegalebadrane.it`
- `POSTGRES_PASSWORD`: 32+ caratteri random (`python -c "import secrets; print(secrets.token_urlsafe(32))"`).

**Mai** committare `.env.staging`. Verifica con `git status` che non
appaia modificato (è in `.gitignore`).

## 5. Bind del web container al loopback host

Caddy gira sul host, il container `web` espone solo `8000` sulla rete
docker. Per farli parlare crea un override compose che pubblica `8000`
su `127.0.0.1` (mai sull'IP pubblico):

```bash
cat > docker-compose.staging.override.yml <<'EOF'
services:
  web:
    ports:
      - "127.0.0.1:8000:8000"
EOF
```

Questo file **non** è in repo (lascialo locale al VPS). I comandi
`scripts/staging/up.sh` continuano a funzionare: docker compose
applica automaticamente l'override se presente accanto al file
principale.

## 6. Trasferimento PDF G.U. + CSV TUN

Sul tuo laptop (i due file NON sono in repo):

```bash
scp legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf \
    deploy@staging.studiolegalebadrane.it:/opt/badrane-legaltech/legal_data/sources/italy/tun_2025/

scp legal_data/sources/italy/tun_2025/tun_2025_rows.csv \
    deploy@staging.studiolegalebadrane.it:/opt/badrane-legaltech/legal_data/sources/italy/tun_2025/
```

Sul VPS, verifica hash PDF:

```bash
sha256sum legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf
# Atteso: 74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92
```

## 7. Avvio stack

```bash
./scripts/staging/up.sh
docker compose -f docker-compose.staging.yml ps
docker compose -f docker-compose.staging.yml logs --tail 50 web
```

Atteso: `db` e `web` entrambi `Up (healthy)`. Il command del web fa
`migrate` + `collectstatic` automaticamente.

Verifica reachability locale (PRIMA di Caddy):

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
# Atteso: 200 (o 301/302 se DJANGO_SECURE_SSL_REDIRECT=True; in tal caso
# usa: curl -sS -o /dev/null -w "%{http_code}\n" -H "X-Forwarded-Proto: https" http://127.0.0.1:8000/)
```

## 8. Configura Caddy

```bash
# 1. Genera l'hash basic_auth
caddy hash-password
# (incolla la password staging Studio, copia l'hash)

# 2. Copia e personalizza il file example
sudo cp docs/deploy/Caddyfile.staging.example /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile
#    - sostituisci STAGING_DOMAIN con staging.studiolegalebadrane.it
#    - sostituisci email ACME
#    - sostituisci REPLACE_WITH_BCRYPT_HASH_FROM_caddy_hash_password

# 3. Valida e reload
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
sudo journalctl -u caddy -n 100 --no-pager   # cerca "certificate obtained"
```

Test esterno (richiede DNS già risolto):

```bash
curl -sSI https://staging.studiolegalebadrane.it/
# Atteso: HTTP/2 401 Unauthorized (basic auth attivo)
curl -sSI -u staff:<password> https://staging.studiolegalebadrane.it/
# Atteso: HTTP/2 200 OK
```

## 9. Bootstrap dati TUN

```bash
./scripts/staging/manage.sh createsuperuser
./scripts/staging/bootstrap_italy_tun.sh
```

Atteso al termine: source `needs_review`, dataset `draft`, formula
`draft`, righe `9191`. Lo script NON promuove a `approved`: è atto
umano (vedi sotto).

## 10. Approvazione legale staging

Vedi `STAGING_DEPLOY.md §6` per la procedura completa
(`formula.parameters` + `LegalReview` + promozione status).

In sintesi via shell:

```bash
./scripts/staging/manage.sh shell
```

```python
from datetime import date
from apps.legal_sources.models import LegalSource, LegalReview
from apps.legal_sources.enums import SourceStatus
from apps.compensation.models import CompensationDataset, CalculationFormula, DatasetStatus
from apps.accounts.models import User

reviewer = User.objects.get(username="<superuser>")
src = LegalSource.objects.get(slug="it-dpr-12-2025-tun-danno-biologico")
LegalReview.objects.create(
    source=src, reviewer=reviewer,
    decision=LegalReview.Decision.APPROVE,
    previous_status=src.status, new_status=SourceStatus.APPROVED,
    comment="Formal Studio approval — staging deploy.",
)
src.status = SourceStatus.APPROVED
src.legal_reviewer = reviewer
src.last_checked_at = date.today()
src.save(update_fields=["status", "legal_reviewer", "last_checked_at"])
ds = CompensationDataset.objects.get(version_label="DPR-12-2025")
ds.status = DatasetStatus.APPROVED
ds.save(update_fields=["status"])
fm = CalculationFormula.objects.get(code="italy_art_138_tun_2025_base")
fm.status = DatasetStatus.APPROVED
fm.save(update_fields=["status"])
```

`formula.parameters` runtime via admin (vedi `STAGING_DEPLOY.md §6.1`).

## 11. Smoke test

```bash
./scripts/staging/smoke.sh
```

Atteso:
```
status: calculated
estimated_min: 21709.0000
estimated_mid: 21709.0000
estimated_max: 21709.0000
SMOKE PASSED.
```

E test funnel pubblico via browser su
`https://staging.studiolegalebadrane.it/wizard/it/road-accident/` con
`(35, 10, 0)` → MIN/MID/MAX = 21.709,00 EUR.

## 12. Backup giornaliero

### 12.1. DB Postgres (`pg_dump`)

```bash
./scripts/staging/backup_db.sh
# → backups/staging_<ts>.sql
ls -lh backups/
```

Schedule via cron utente `deploy`:

```bash
crontab -e
```

```cron
# Ogni notte 02:00 dump DB; pulisce dump > 14 giorni.
0 2 * * * cd /opt/badrane-legaltech && ./scripts/staging/backup_db.sh >> /var/log/badrane-backup.log 2>&1
0 3 * * * find /opt/badrane-legaltech/backups -name 'staging_*.sql' -mtime +14 -delete
```

### 12.2. Media (PDF reports + allegati)

```bash
docker run --rm \
    -v badrane-legaltech_media_data:/data:ro \
    -v $(pwd)/backups:/backup \
    alpine sh -c "tar czf /backup/media_$(date +%Y%m%d_%H%M%S).tar.gz -C /data ."
```

Aggiungi al cron in coda al backup DB.

### 12.3. Off-site (raccomandato)

`rclone` o `aws s3 sync` verso bucket cifrato (Hetzner Storage Box,
Backblaze B2, Scaleway Object Storage). Esempio rclone:

```bash
sudo apt install -y rclone
rclone config   # configura remote `staging-offsite` cifrato
# In coda al cron:
0 4 * * * rclone copy /opt/badrane-legaltech/backups staging-offsite:badrane-staging --include "*.sql" --include "*.tar.gz"
```

### 12.4. Test restore (almeno una volta a trimestre)

**Su un host secondario o in un container scratch**, mai su staging
attiva. Procedura:

```bash
# DB restore
docker compose -f docker-compose.staging.yml stop web
cat backups/staging_<ts>.sql | docker compose -f docker-compose.staging.yml \
    exec -T db psql -U badrane badrane_staging
docker compose -f docker-compose.staging.yml start web
./scripts/staging/smoke.sh   # deve tornare 21.709

# Media restore
docker compose -f docker-compose.staging.yml stop web
docker run --rm \
    -v badrane-legaltech_media_data:/data \
    -v $(pwd)/backups:/backup \
    alpine sh -c "rm -rf /data/* && tar xzf /backup/media_<ts>.tar.gz -C /data"
docker compose -f docker-compose.staging.yml start web
```

Documenta la data dell'ultimo test riuscito; un backup non testato è un
backup ipotetico.

## 13. Rollback

### Application code

```bash
git log --oneline -10
git checkout <previous-commit>
./scripts/staging/up.sh
```

### Database

Vedi §12.4 — è la stessa procedura, applicata a un dump scelto.
**Conferma sempre prima di eseguire**: il `psql` sovrascrive il DB
in-place senza prompt.

### Caddy config

```bash
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak.$(date +%s)
# edit
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy   # zero-downtime
```

In caso di certificato perso (scadenza, rate-limit ACME): Caddy
mantiene un fallback `local_certs` solo se abilitato. Per forzare
una rinegoziazione:
`sudo systemctl restart caddy && sudo journalctl -u caddy -f`.

## 14. Monitoring minimo

Almeno tre check, anche solo via cron + email:

```bash
# Liveness Caddy + web
curl -fsS -u staff:<pwd> https://staging.studiolegalebadrane.it/ -o /dev/null

# Wizard accessibile
curl -fsS -u staff:<pwd> https://staging.studiolegalebadrane.it/wizard/ -o /dev/null

# Backup esistente delle ultime 24h
find /opt/badrane-legaltech/backups -name 'staging_*.sql' -mtime -1 | grep -q .
```

In prod servirà uptime monitor esterno (Uptime Kuma / better-stack /
healthchecks.io) + Sentry SDK per Django — vedi `PRODUCTION_PREFLIGHT.md`.

## 15. Go / no-go staging

### Condizioni "staging pronto"

Tutti i seguenti devono essere veri:

- [ ] DNS `staging.studiolegalebadrane.it` risolve all'IP VPS.
- [ ] `https://staging.studiolegalebadrane.it/` risponde 401 senza
      credenziali e 200 con basic auth.
- [ ] Caddy ha certificato Let's Encrypt valido (verificabile da
      browser con icona lucchetto + scadenza > 30 giorni).
- [ ] `docker compose ps` mostra `web` e `db` `Up (healthy)`.
- [ ] `./scripts/staging/smoke.sh` torna `SMOKE PASSED.` con `21709`.
- [ ] Funnel pubblico via browser dà MIN/MID/MAX = 21.709,00 EUR e
      PDF download 200.
- [ ] Cron backup DB ha prodotto almeno un dump > 0 byte.
- [ ] Test restore eseguito almeno una volta su host secondario.
- [ ] `.env.staging` ha permessi 600, owner `deploy`.
- [ ] `ufw status` mostra solo 22/80/443 aperte.
- [ ] Login root ssh disabilitato, password ssh disabilitate.

### Condizioni "non procedere"

Se uno di questi è vero, **non aprire l'URL ai clienti**:

- Certificato self-signed o `local_certs` ancora attivo.
- Basic auth assente o con hash placeholder `REPLACE_WITH_...`.
- `.env.staging` con `DJANGO_DEBUG=True`.
- Smoke test non torna `21709`.
- Source/dataset/formula non in stato `approved` (calculator
  restituisce `unavailable_requires_legal_validation`).
- Backup DB mai eseguito o di dimensione 0.
- Volumi docker non persistenti (es. `down -v` accidentale).

## 16. Cosa resta fuori scope (rimanda a PRODUCTION_PREFLIGHT.md)

- Cookie consent banner EU + Privacy Policy linkata.
- MFA su admin Django.
- Email transactional (notifica Lead allo Studio).
- Rate-limit applicativo sui POST pubblici.
- Sentry / APM.
- Off-site backup automatizzato cifrato.
- Procedure GDPR di cancellazione dati (`erasure` workflow).
- Disaster recovery cross-region.

Tutti questi punti vanno chiusi PRIMA di esporre l'URL pubblico a utenti
reali. Lo staging con basic auth è un ambiente di test interno: ottimo
per QA Studio, non sostituibile alla produzione.
