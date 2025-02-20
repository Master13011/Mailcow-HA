# Intégration Mailcow pour Home Assistant

Cette intégration personnalisée permet de connecter votre serveur Mailcow à Home Assistant, offrant une visibilité en temps réel sur l'état et les performances de votre infrastructure de messagerie.

## Fonctionnalités

- **Surveillance des boîtes aux lettres** : Affiche le nombre total de boîtes aux lettres gérées par votre serveur Mailcow.
- **Suivi des domaines** : Montre le nombre de domaines configurés sur votre serveur Mailcow.
- **Version de Mailcow** : Indique la version actuelle de votre installation Mailcow.
- **État du service Vmail** : Surveille l'utilisation du disque pour le service de messagerie virtuelle (Vmail).
- **Statut des conteneurs** : Fournit un aperçu de l'état de tous les conteneurs Docker associés à Mailcow.

## Installation

 Ensure that [HACS](https://hacs.xyz) is installed.

2. Open HACS, then select `Integrations`.

3. Select &#8942; and then `Custom repositories`.

4. Set `Repository` to *https://github.com/Master13011/Mailcow-HA*  
   and `Category` to _Integration_.

5. Install **Mailcow-HA** integration via HACS:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Master13011&repository=Mailcow-HA)

   If the button doesn't work: Open `HACS` > `Integrations` > `Explore & Download Repositories` and select integration `Mailcow HA`.

## Configuration

Depuis vote Interface Admin Mailcow (https://mail.domainmailcow.com/admin), activer votre API.

![image](https://github.com/user-attachments/assets/8ecac93c-2acd-457d-8170-57b99ddb9257)

Les API de votre instance sont disponibles ici : https://mail.domainmailcow.com/api/#/

Fonctionnalité :
**Status**

GET
/api/v1/get/status/containers

GET
/api/v1/get/status/vmail

GET
/api/v1/get/status/version

## Utilisation

Une fois installée et configurée, l'intégration Mailcow ajoutera plusieurs capteurs à votre instance Home Assistant, vous permettant de surveiller facilement l'état de votre serveur Mailcow depuis votre tableau de bord Home Assistant.

## Contribution

Les contributions à ce projet sont les bienvenues. N'hésitez pas à soumettre des pull requests ou à ouvrir des issues pour des suggestions d'amélioration ou des rapports de bugs.
