# LOCAL — Product hardening, pass 5 — admin MFA gating (opt-in)

**Iter**: F-local-product-hardening-pass5-mfa-admin
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**
**Default**: `ADMIN_MFA_REQUIRED=False` ⇒ il guard è no-op in dev.

> Quinto passaggio: scaffolding di MFA (TOTP) per il Django
> admin, con un middleware leggero che fa **pass-through di
> default** e si attiva solo via env (`ADMIN_MFA_REQUIRED=True`).
> Nessun dato legale toccato. IT smoke 35/10/0 → 26 268 / 27 353
> / 28 439 EUR verificato dal canarino.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| Dependency | `requirements.txt` | aggiunti `django-otp>=1.5,<2` e `qrcode>=7.4,<9` (NON in INSTALLED_APPS) |
| Module | `apps/core/admin_mfa.py` (nuovo) | `is_user_mfa_verified` + `AdminMFAMiddleware` |
| Settings | `config/settings.py` | `ADMIN_MFA_REQUIRED=False` env-driven |
| Middleware | `config/settings.py::MIDDLEWARE` | aggiunto `apps.core.admin_mfa.AdminMFAMiddleware` |
| Template | `templates/admin/mfa_required.html` (nuovo) | pagina HTTP 403 di enforcement |
| Test | `apps/core/test_admin_mfa.py` (nuovo) | 7 test |
| Docs | questo file | — |

Nessun cambio a calculator/engine/wizard/dataset/formula. Nessuna
nuova migrazione: django-otp **NON** è in `INSTALLED_APPS` per
evitare schema migrations premature su ambienti dev.

---

## 2. Scelta tecnica MFA

Valutazione delle opzioni:

| Opzione | Pro | Contro | Decisione |
|---|---|---|---|
| `django-otp` + `otp_totp` | Standard de facto, manutenuto, integrazione admin via mixin | Richiede migrations, app extra in INSTALLED_APPS | **Adottata come stack di riferimento per produzione**, ma non attivata in INSTALLED_APPS in pass 5 |
| `django-two-factor-auth` | Wraps django-otp con UI integrata | Più dipendenze (django-formtools, ecc.), più magic | Considerata; può essere adottata in un pass successivo se serve UX OOTB |
| Custom session-based | Zero dipendenze | Reinventiamo la ruota; meno robusto | Usata SOLO come fallback testing |

**Strategia pass 5:** middleware proprio + hook duck-typed che
funziona con o senza django-otp installato:
- Se `django-otp` è installato + `OTPMiddleware` attivo,
  `request.user.is_verified()` è già disponibile → il guard la usa.
- Altrimenti, fallback a `request.session["mfa_verified"]==True`,
  utile per:
  - test locali (no dep installata);
  - eventuale flusso custom Studio (es. step verifica via flusso
    proprietario).

**Pacchetti aggiunti a `requirements.txt`:**

```
django-otp>=1.5,<2
qrcode>=7.4,<9
```

`qrcode` serve per generare il QR del TOTP secret durante
l'enrollment device. Pinning `<2` per stabilità: eventuali break
changes della 2.x verranno valutati separatamente.

**Stato d'installazione**: dichiarata in requirements, **non
necessariamente installata** nel venv dev. Il guard funziona
comunque (fallback session-based).

---

## 3. Settings

In `config/settings.py`, sezione **MFA admin**:

| Setting | Default | Override env |
|---|---|---|
| `ADMIN_MFA_REQUIRED` | `False` | `ADMIN_MFA_REQUIRED` |

In `MIDDLEWARE`, aggiunta dopo `AuthenticationMiddleware`:

```python
"apps.core.admin_mfa.AdminMFAMiddleware",
```

La posizione è importante: il middleware accede a `request.user`,
quindi deve girare **dopo** `AuthenticationMiddleware`.

**Comportamento:**
- `ADMIN_MFA_REQUIRED=False` (default dev): pass-through totale.
- `ADMIN_MFA_REQUIRED=True`: gating attivo su `/admin/` (non
  pubblico, non `/healthz/`, non `/admin/login/`, non
  `/admin/logout/`).

---

## 4. Guard admin — comportamento

`AdminMFAMiddleware.__call__(request)` esegue questi check in
ordine:

1. **Flag check**: se `ADMIN_MFA_REQUIRED=False` → pass-through.
2. **Path scope**: se `path` non inizia con `/admin/` → pass-through
   (la home pubblica, `/healthz/`, `/wizard/...`, `/contact/`
   restano fuori).
3. **Loop-safe bypass**: `/admin/login/` e `/admin/logout/`
   bypassano sempre. Senza questo bypass, un staff non verificato
   non potrebbe né raggiungere il form login né disconnettersi.
4. **Anonymous**: se `request.user` non è autenticato → pass-through.
   Django admin mostra il suo redirect a `/admin/login/`. Il
   guard non aggiunge sovrapposizioni.
5. **Non-staff**: se `is_staff=False` → pass-through. Django admin
   risponde 403 da solo, non duplichiamo il messaggio.
6. **Staff con MFA verificato**: pass-through.
7. **Staff senza MFA verificato**: render
   `templates/admin/mfa_required.html` con HTTP 403.

### 4.1 Hook `is_user_mfa_verified(user, request) -> bool`

Pubblico, sostituibile/estendibile. Algoritmo:

```python
def is_user_mfa_verified(user, request) -> bool:
    if user is None or not user.is_authenticated:
        return False
    # 1. django-otp (se installato + cabled)
    fn = getattr(user, "is_verified", None)
    if callable(fn):
        try:
            if fn():
                return True
        except Exception:
            pass
    # 2. Session flag (test/custom)
    if request and request.session.get("mfa_verified") is True:
        return True
    return False
```

**Mai solleva**: in caso di errore inatteso il middleware loggava
warning e ricade su False (deny per sicurezza).

### 4.2 Pagina di enforcement

`templates/admin/mfa_required.html`: HTML statico stand-alone (non
estende `base.html` — l'admin ha un suo design, e questa è una
pagina tecnica che non deve dipendere da partials di brand).
Include:
- titolo chiaro "Multi-factor authentication required";
- istruzioni minimal: logout, setup TOTP, sign in di nuovo;
- link a `/admin/logout/`;
- `noindex, nofollow`.

---

## 5. Come configurare un device TOTP (procedura prevista)

> Questa procedura **non è automatizzata** in pass 5. È il
> percorso di attivazione previsto per quando lo Studio sarà
> pronto a girare con `ADMIN_MFA_REQUIRED=True`.

### 5.1 Installazione (in venv staging/prod)

```bash
pip install -r requirements.txt
```

### 5.2 Attivazione django-otp in settings

```python
INSTALLED_APPS = [
    ...
    "django_otp",
    "django_otp.plugins.otp_totp",
    ...
]

MIDDLEWARE = [
    ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",  # ← AGGIUNGERE
    ...
    "apps.core.admin_mfa.AdminMFAMiddleware",
]
```

**Importante**: l'ordine nella `MIDDLEWARE` list richiede che
`OTPMiddleware` venga **prima** del nostro `AdminMFAMiddleware`:
solo così `request.user.is_verified()` è disponibile per il guard.

### 5.3 Migrate

```bash
python manage.py migrate
```

Crea le tabelle `otp_totp_*` per i device.

### 5.4 Enrollment device per uno staff

Via `manage.py shell`:

```python
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_totp.models import TOTPDevice

user = get_user_model().objects.get(username="alice")
device = TOTPDevice.objects.create(user=user, name="alice-yubikey")
print(device.config_url)  # otpauth://...
# Scansionare il URL con un'app TOTP (Aegis, Google Authenticator, ...)
device.confirmed = True
device.save()
```

### 5.5 Attivare il guard

```bash
export ADMIN_MFA_REQUIRED=True
```

Da quel momento, `/admin/` per staff senza device verificato
risponde 403 con la pagina di enforcement.

---

## 6. Comportamento per ambiente

| Ambiente | `ADMIN_MFA_REQUIRED` | Conseguenza |
|---|---|---|
| **Dev locale** | `False` (default) | admin login standard. Nessuna friction. |
| **Staging** | `False` o `True` (a scelta Studio) | Se `True`, è il rehearsal del flusso prod. |
| **Production** | **`True` obbligatorio** | Nessun staff senza TOTP firmato accede ad admin. |

In dev, anche se uno sviluppatore vuole testare `True` senza
configurare django-otp, può:
1. Loggarsi normalmente.
2. Aprire `manage.py shell` e settare `request.session["mfa_verified"]=True`
   (oppure usare il pattern test: `client.session["mfa_verified"]=True`).

---

## 7. Limiti pass 5

- **No UI di enrollment**: non c'è una vista admin per registrare
  un nuovo device. Si fa via shell (procedura 5.4) o tramite
  `django_otp.plugins.otp_totp` admin se l'app è in INSTALLED_APPS.
- **Nessun recovery code**: se un device si perde, l'unica strada
  oggi è eliminare il TOTPDevice via shell con un superuser e
  re-enrollare. Pass futuro deve aggiungere `otp_static` per i
  recovery codes.
- **Nessun rate-limit OTP**: `django-otp` non ha rate-limit
  built-in robusto. Da combinare con il rate-limit pass 1
  + un eventuale lock-out (django-axes) in produzione.
- **No SMS/email OTP**: per scelta. SMS è insicuro
  (SIM-swap), email è un secondo fattore weak. Solo TOTP/U2F.
- **Niente WebAuthn/Passkeys**: contemplato per un pass futuro
  (richiede `django-fido2` o stack equivalente).

---

## 8. Test aggiunti (7, tutti passati)

In `apps/core/test_admin_mfa.py`:

| # | Test | Verifica |
|---|---|---|
| 1 | `test_admin_login_flow_normal_when_mfa_disabled` | Flag off: `/admin/login/` 200, `/admin/` redirect to login |
| 2 | `test_healthz_is_not_gated_by_admin_mfa` | `/healthz/` 200 anche con flag on |
| 3 | `test_public_home_is_not_gated_by_admin_mfa` | home pubblica 200 anche con flag on |
| 4 | `test_anonymous_on_admin_redirects_to_login_when_mfa_required` | anonymous → 302 verso `/admin/login/` (no 403) |
| 5 | `test_staff_without_verified_mfa_is_blocked` | staff loggato senza MFA → 403 + body contiene "Multi-factor authentication required" |
| 6 | `test_staff_with_session_mfa_verified_passes_through` | con `session["mfa_verified"]=True`, status `!= 403` |
| 7 | `test_italy_smoke_run_simulation_35_10_0` | 35/10/0 → 26 268 / 27 353 / 28 439 |

I test sono pure-Python: NON richiedono `django-otp` installato.
Il fallback session-based copre il path "MFA verificato" senza
dover seedare `TOTPDevice`.

---

## 9. Cosa resta per produzione

### 9.1 Recovery codes
- Aggiungere `django_otp.plugins.otp_static` a `INSTALLED_APPS`.
- Generare 8–10 codici one-time per ogni staff al momento
  dell'enrollment.
- Procedure di archiviazione sicura (cassaforte digitale,
  password manager Studio).

### 9.2 Policy staff
- **Tutti** gli staff/superuser devono avere almeno 1 TOTP device
  prima del rollout di `ADMIN_MFA_REQUIRED=True`.
- Audit periodico (script che lista staff senza device confermato).
- Rotazione device (es. ogni 12 mesi).

### 9.3 Backup superuser
- Rischio lock-out: se l'unico superuser perde il device, l'admin
  diventa irraggiungibile.
- Soluzione: un superuser di break-glass dedicato, con device su
  hardware key offline (es. YubiKey custodita in cassaforte
  Studio).

### 9.4 Logging accessi admin
- Audit log di ogni `admin.login.success` e `admin.login.failed`
  con: username, IP, user-agent, timestamp.
- Alert su `admin.login.failed` ripetuti per lo stesso username
  (brute force).
- Già parzialmente coperto da `auditlog` middleware: estendere
  in pass futuro con dashboard staff.

### 9.5 IP allowlist / reverse proxy
- Caddy/Nginx davanti all'app: `/admin/` accessibile solo da IP
  Studio o da VPN (`require ip 192.168.x.0/24`).
- Combinabile con `ADMIN_MFA_REQUIRED=True` per defense-in-depth.

### 9.6 Rate-limit OTP
- `django-axes` per lock-out su brute-force OTP.
- Configurazione: 5 tentativi falliti → lock 30 min, alert al
  staff manager.

---

## 10. Validazione

```bash
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

---

## 11. Disclaimer

Questo iter aggiunge uno scaffolding MFA opzionale e
non-invasivo. Non altera dati legali, calcoli, o l'output del
calcolatore Italia. L'attivazione effettiva (`ADMIN_MFA_REQUIRED=True`)
resta in capo allo Studio quando il flusso di enrollment device
sarà completo. Il disclaimer obbligatorio CLAUDE.md sulle
simulazioni indicative resta valido.
