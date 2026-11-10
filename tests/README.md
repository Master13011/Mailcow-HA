# Tests — Intégration Mailcow pour Home Assistant

Ce document décrit les tests automatisés de l'intégration `mailcow_ha_custom`.
Ils sont placés dans le dossier `tests/` et s'exécutent avec **pytest**.

## Principes

- **Aucun accès réseau** : le client HTTP (`aiohttp`) est remplacé par une fausse session (`FakeSession`, `FakeResponse`, `FakeContext`). Aucun serveur Mailcow réel n'est nécessaire.
- Les fonctions utilitaires (`util.py`) sont testées comme des fonctions pures, sans Home Assistant.
- Les tests sont lancés automatiquement par GitHub Actions (`.github/workflows/tests.yml`) sur **Python 3.13 et 3.14** à chaque push et pull request sur `main`/`master`.

## Lancer les tests

```bash
pip install -r requirements.txt
pytest -q
```

La configuration (`pytest.ini`) fixe `pythonpath = .` et `testpaths = tests`.

## Contenu des tests

### `tests/test_api.py` — client API (`MailcowAPI`)

| Test | Ce qui est vérifié |
|---|---|
| `test_auth_errors_are_preserved` (401, 403) | Un refus d'authentification lève `MailcowAuthenticationError` (et non une erreur générique). |
| `test_http_errors_are_api_errors` (404, 500, 503) | Les autres codes HTTP en erreur lèvent `MailcowAPIError`, sans être confondus avec une erreur d'authentification ou de connexion ; le code HTTP figure dans le message. |
| `test_invalid_json` | Une réponse 200 dont le JSON est invalide lève `MailcowAPIError`. |
| `test_error_payload_with_auth_message` | Une réponse 200 contenant `{"type": "error", "msg": "authentication failed"}` est traitée comme une erreur d'authentification. |
| `test_error_payload_generic` | Une réponse 200 contenant un autre message d'erreur lève `MailcowAPIError`. |
| `test_timeout_and_connection_errors` | Un délai dépassé (`TimeoutError`) ou une erreur `ClientError` lève `MailcowConnectionError`. |
| `test_ssl_error` | Une erreur de certificat (`ClientSSLError`) lève `MailcowSSLError`. |
| `test_success_and_url_building` | Cas nominal : la version est renvoyée, l'URL est bien construite (`https://mail.example.com/api/v1/get/status/version`) et l'en-tête `X-API-Key` est envoyé. |
| `test_counts_and_shapes` | Nombre de boîtes aux lettres (liste de 3 éléments → 3) ; un dictionnaire vide pour les domaines donne `None` ; une réponse inattendue pour les conteneurs donne une liste vide. |
| `test_normalize_base_url` (5 cas) | Normalisation de l'URL saisie : ajout de `https://`, suppression des espaces, du `/` final, de la requête et du fragment ; conservation du port et du schéma `http://`. |
| `test_normalize_base_url_invalid` (5 cas) | Rejet (`MailcowInvalidURLError`) d'une URL vide, composée d'espaces, en `ftp://`, sans hôte ou avec un port invalide (`99999`). |

### `tests/test_util.py` — fonctions utilitaires

| Test | Ce qui est vérifié |
|---|---|
| `test_parse_version` | Analyse des versions Mailcow (`2025-03` → `(2025, 3, "")`, `2025-03a` → suffixe `a`) ; `None` pour une valeur inconnue ou absente. |
| `test_is_newer` | Comparaison de versions (suffixes `a`, `b`… pris en compte, passage d'une année à l'autre) ; pour un format inconnu, repli sur la simple inégalité. |
| `test_latest_from_tags_ignores_non_versions` | La dernière version est extraite d'une liste de tags GitHub en ignorant `nightly`, `1.0`, etc. ; liste vide ou type invalide → `None`. |
| `test_night_hours` | La pause nocturne couvre 23h00–05h00 (23, 0 et 4 sont « nuit » ; 5, 12 et 22 ne le sont pas). |
| `test_vmail_percent` | Conversion du pourcentage d'occupation Vmail (`"55%"`, `12`) ; `None` si la valeur est illisible, absente ou si les données sont `None`. |
| `test_containers_state` | État global des conteneurs : `All Running`, `Issues Detected`, `No Data` ou `N/A` selon les données (dictionnaire, liste, vide, invalide). |
| `test_containers_attributes` | Construction des attributs à partir d'un dictionnaire ou d'une liste de conteneurs ; dictionnaire vide si les données sont `None`. |
| `test_sanitize_url_is_stable` | La transformation de l'URL en identifiant est stable (`https://mail.example.com` → `httpsmailexamplecom`). |

## Périmètre non couvert

Les modules `config_flow.py`, `options_flow.py`, `coordinator.py`, `sensor.py`, `update.py` et `__init__.py` ne sont pas couverts par des tests automatisés pour le moment ; les tests actuels portent sur le client API et les utilitaires.
