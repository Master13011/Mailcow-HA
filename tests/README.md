# Tests — Intégration Mailcow pour Home Assistant

Ce document décrit les tests automatisés de l'intégration `mailcow_ha_custom`.
Ils sont placés dans le dossier `tests/` et s'exécutent avec **pytest**.

## Principes

- **Aucun accès réseau** : le client HTTP (`aiohttp`) est remplacé par de fausses sessions (`FakeSession` pour l'API Mailcow, `FakeGithubSession` pour GitHub) ou par une fausse API (`make_api`). Aucun serveur Mailcow ni GitHub réel n'est nécessaire.
- Les fonctions utilitaires (`util.py`) et les exceptions sont testées comme des fonctions pures, sans Home Assistant.
- Les autres modules (config flow, options, coordinateur, capteurs, mise à jour) sont testés avec la fixture `hass` de `pytest-homeassistant-custom-component`.
- Helpers communs : `tests/common.py` (`make_entry`, `make_api`, `setup_entry`, `FakeGithubSession`…) et `tests/conftest.py` (activation de l'intégration personnalisée, fixture `mailcow_api` qui simule un serveur Mailcow en bon état).
- Les tests sont lancés automatiquement par GitHub Actions (`.github/workflows/tests.yml`) sur **Python 3.13 et 3.14** à chaque push et pull request sur `main`/`master`.

## Lancer les tests

```bash
pip install -r requirements.txt
pytest -q
```

La configuration (`pytest.ini`) fixe `pythonpath = .`, `asyncio_mode = auto` et `testpaths = tests`. Les dépendances de test (dont `pytest-homeassistant-custom-component`) sont dans `requirements.txt`.

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

### `tests/test_api.py` — compléments

| Test | Ce qui est vérifié |
|---|---|
| `test_each_method_calls_its_endpoint` (5 méthodes) | Chaque méthode appelle son point d'entrée : `status/version`, `mailbox/all`, `domain/all`, `status/vmail`, `status/containers`. |
| `test_request_headers_and_timeout` | En-têtes `X-API-Key` et `Accept: application/json`, délai maximal de 15 s. |
| `test_base_url_property_is_normalized` | `base_url` renvoie l'URL normalisée. |
| `test_invalid_url_is_refused_at_construction` | Une URL invalide est refusée dès la création du client. |
| `test_error_payload_with_denied_message` | Un message `Access DENIED` dans une réponse 200 est traité comme une erreur d'authentification. |
| `test_error_payload_without_message` | Une réponse d'erreur sans message lève `MailcowAPIError` (et non une erreur d'authentification). |
| `test_version_shapes` | Version `None` si la réponse est une liste ou ne contient pas `version`. |
| `test_counts_for_an_empty_list` | Une liste vide donne 0 boîte et 0 domaine. |
| `test_vmail_shapes` | Le dictionnaire Vmail est renvoyé tel quel ; une réponse inattendue donne `{}`. |
| `test_containers_shapes_are_returned_unchanged` | Les conteneurs (dictionnaire ou liste) sont renvoyés sans modification. |

Les tests de ce fichier sont désormais asynchrones (`async def`), ce qui évite `asyncio.run()` avec le plugin Home Assistant.

### `tests/test_util.py` — compléments

| Test | Ce qui est vérifié |
|---|---|
| `test_parse_version_rejects_malformed_values` (9 cas) | `2025-3`, `25-03`, `2025-03ab`, `2025-03A`, `v2025-03`, chaîne vide, entier, `None`… → `None`. |
| `test_parse_version_ignores_surrounding_spaces` | Les espaces autour de la version sont ignorés. |
| `test_is_newer_edge_cases` (6 cas) | Suffixes (`b` > `a`, absence de suffixe < `a`), changement d'année, version identique, format inconnu. |
| `test_latest_from_tags_skips_invalid_entries` | Entrées `None`, sans nom ou au nom non textuel ignorées. |
| `test_latest_from_tags_does_not_depend_on_the_order` | Le résultat ne dépend pas de l'ordre des tags ; aucun tag valide → `None`. |
| `test_night_window_for_every_hour` (24 cas) | Chaque heure de 0 à 23 : « nuit » de 23h00 à 04h59. |
| `test_vmail_percent_formats` / `test_vmail_percent_unusable_inputs` | `" 55 % "`, `"12.5%"`, `0`, `"100"` ; types inattendus ou valeur `None` → `None`. |
| `test_containers_state_edge_cases` | Conteneur arrêté ou sans état → `Issues Detected` ; liste vide → `No Data` ; éléments invalides → `N/A`. |
| `test_containers_attributes_edge_cases` | Dictionnaire renvoyé tel quel ; liste indexée par nom de conteneur ou par position ; type invalide → `{}`. |
| `test_sanitize_url_keeps_only_alphanumeric_characters` | Port, chemin et chaîne vide. |

### `tests/test_exceptions.py` — exceptions

| Test | Ce qui est vérifié |
|---|---|
| `test_every_error_is_a_mailcow_api_error` | Toutes les erreurs dérivent de `MailcowAPIError`. |
| `test_ssl_error_is_a_connection_error` | `MailcowSSLError` dérive de `MailcowConnectionError` (le config flow s'appuie sur cet ordre). |
| `test_error_families_do_not_overlap` | L'authentification, la connexion et l'URL invalide ne se confondent pas. |
| `test_message_is_used_as_text` / `test_class_name_is_used_without_message` | Le texte de l'erreur est le message, ou le nom de la classe sans message. |

### `tests/test_coordinator.py` — coordinateur

| Domaine | Ce qui est vérifié |
|---|---|
| Paramètres | Intervalle par défaut 10 min, valeurs des options (`5`, `"30"`, `1440`), jamais 0 minute (`0` et `-5` → 1), valeur invalide (`"abc"`, `None`) → 10 ; option de pause nocturne. |
| Mise à jour | Toutes les valeurs sont renvoyées ; chaque point d'entrée est appelé une fois ; un échec de GitHub ne fait pas échouer la mise à jour. |
| Erreurs | Erreur d'authentification → `ConfigEntryAuthFailed` (prioritaire sur les autres erreurs) ; autres erreurs → `UpdateFailed` ; GitHub n'est pas interrogé si Mailcow échoue. |
| Pause nocturne | Aux heures 23, 0, 3 et 4 les anciennes valeurs sont conservées sans appel à l'API ; aux heures 5, 12 et 22 la mise à jour a lieu ; la première actualisation a toujours lieu ; pause désactivée → mise à jour la nuit. |
| Version GitHub | Tag de la dernière release ; repli sur les tags si la release est absente, vide ou invalide ; en-têtes et délai de 10 s ; échec des deux sources, erreurs réseau, timeout, JSON invalide → pas de version. |
| Cache | Version mise en cache 6 h ; nouvel essai au bout de 15 min après un échec ; l'ancienne version est conservée quand un rafraîchissement échoue. |

### `tests/test_init.py` — installation et migration

| Domaine | Ce qui est vérifié |
|---|---|
| Cycle de vie | Installation (`LOADED`), coordinateur stocké dans `runtime_data`, déchargement (`NOT_LOADED`) ; 5 capteurs et 1 entité de mise à jour créés. |
| Vérification TLS | `verify_ssl` de l'entrée appliqué à la session Mailcow (actif par défaut) ; la session GitHub est toujours vérifiée. |
| Échecs | Clé API absente ou refusée → `SETUP_ERROR` et lancement de la réauthentification ; URL invalide → `SETUP_ERROR` ; serveur injoignable → `SETUP_RETRY`. |
| Migration 1 → 2 | Clé API déplacée des options vers les données (celle des options l'emporte) ; `verify_ssl` ajouté (actif par défaut, valeur existante conservée) ; URL normalisée ; identifiant unique en minuscules, conservé s'il existe déjà, non réutilisé s'il est pris ; URL invalide conservée ; autres options conservées ; entrée vide tolérée. |
| Versions | Entrée déjà en version 2 inchangée ; version plus récente refusée. |

### `tests/test_config_flow.py` — assistant de configuration

| Domaine | Ce qui est vérifié |
|---|---|
| Création | Entrée « Mailcow » avec URL normalisée, clé, `verify_ssl`, options par défaut et identifiant unique ; identifiants testés sur l'URL normalisée. |
| Saisie | URL avec espaces, majuscules, port et `/` final normalisée ; options choisies conservées (intervalle converti en entier) ; choix TLS appliqué à la session. |
| URL invalide | Vide, espaces, `ftp://`, port invalide → `invalid_url`, sans aucun appel réseau. |
| Erreurs | Authentification → `invalid_auth` ; certificat → `ssl_error` ; connexion ou erreur API ou version vide → `cannot_connect` ; erreur inattendue → `unknown` ; la saisie est conservée dans le formulaire ; le flux aboutit après correction. |
| Doublons | Même serveur refusé (`already_configured`), sans tenir compte de la casse ni du `/` final, avant tout appel réseau. |
| Validation | Intervalle 0 ou 1441 refusé. |
| Réauthentification | Nouvelle clé enregistrée (`reauth_successful`), validée sur l'URL de l'entrée ; choix TLS conservé ; mauvaise clé → `invalid_auth` et ancienne clé conservée. |
| Reconfiguration | Clé et TLS mis à jour (`reconfigure_successful`) ; choix TLS actuel proposé ; erreurs `ssl_error`, `cannot_connect`, `invalid_auth` sans modification. |

### `tests/test_options_flow.py` — options

| Test | Ce qui est vérifié |
|---|---|
| Affichage | Le formulaire propose les options actuelles (pause nocturne, intervalle 30). |
| Enregistrement | Options enregistrées (intervalle entier) et intégration **rechargée** avec le nouvel intervalle et la nouvelle pause nocturne. |
| Valeurs par défaut | Sans saisie : pause nocturne désactivée, intervalle 10. |
| Validation | Intervalles 0, -1 et 1441 refusés ; 1 et 1440 acceptés. |

### `tests/test_entity.py` — entité de base

| Test | Ce qui est vérifié |
|---|---|
| Identifiant unique | Format historique conservé (`mailcow_version_httpsmailexamplecom_entry_1`) ; dépend de la clé, de l'URL et de l'entrée. |
| Appareil | Identifiants, nom `Mailcow (mail.example.com)` (port conservé), fabricant, modèle, version logicielle, URL de configuration, type « service » ; version `None` sans données. |
| Intégration | Un seul appareil regroupe toutes les entités. |

### `tests/test_sensor.py` — capteurs

| Domaine | Ce qui est vérifié |
|---|---|
| Descriptions | Les 5 capteurs, clés de traduction, icônes ; Vmail en pourcentage avec classe d'état « mesure ». |
| Valeurs | Version, nombre de boîtes, nombre de domaines, Vmail (55,0), conteneurs (`All Running`) ; sans données : `None` (et `N/A` pour les conteneurs). |
| Attributs | Aucun pour version et compteurs ; Vmail (`status`, `disk`, `used`, `total`, `None` sans données) ; conteneurs à partir d'un dictionnaire ou d'une liste. |
| Avec Home Assistant | États réels des 5 capteurs ; liste des conteneurs en attributs ; conteneur arrêté → `Issues Detected` ; valeurs manquantes → `unknown` ; identifiants uniques historiques. |

### `tests/test_update.py` — entité de mise à jour

| Domaine | Ce qui est vérifié |
|---|---|
| Valeurs | Versions installée et disponible issues du coordinateur (ou `None`) ; lien vers le tag de la release, sinon vers la page des releases. |
| Comparaison | `2025-04` > `2025-03a`, `2025-03b` > `2025-03a` ; version identique ou plus ancienne : pas de mise à jour. |
| Identité | Identifiant unique et titre `Mailcow`. |
| Avec Home Assistant | État `on` (mise à jour disponible, attributs complets), `off` (à jour ou version installée plus récente), `unknown` (GitHub injoignable). |

### `tests/test_translations.py` — traductions et manifeste

| Test | Ce qui est vérifié |
|---|---|
| Clés | `translations/en.json` et `fr.json` ont exactement les mêmes clés que `strings.json`. |
| Textes utilisés par le code | Erreurs du config flow, motifs d'abandon, étapes, étape des options, noms des capteurs et de la mise à jour traduits. |
| Manifeste | Domaine identique à `const.py`, `config_flow`, type « service », `local_polling` ; un fichier existe pour chaque plateforme. |

## Périmètre non couvert

Le module `sensor_descriptions.py` n'est pas testé : il n'est plus utilisé (les descriptions des capteurs sont définies dans `sensor.py`).
