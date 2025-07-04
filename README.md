**[EN](https://github.com/Master13011/Mailcow-HA/blob/main/README_en.md)**

# Intégration Mailcow pour Home Assistant

Cette intégration personnalisée permet de connecter votre serveur Mailcow à Home Assistant, offrant une visibilité en temps réel sur l'état et les performances de votre infrastructure de messagerie .

## Fonctionnalités

- **Surveillance des boîtes aux lettres** : Affiche le nombre total de boîtes aux lettres gérées par votre serveur Mailcow.
- **Suivi des domaines** : Montre le nombre de domaines configurés sur votre serveur Mailcow.
- **Version de Mailcow** : Indique la version actuelle de votre installation Mailcow.
- **Vérification MAJ Mailcow** : Indique si une nouvelle version de votre installation Mailcow est disponible.
- **État du service Vmail** : Surveille l'utilisation du disque pour le service de messagerie virtuelle (Vmail).
- **Statut des conteneurs** : Fournit un aperçu de l'état de tous les conteneurs Docker associés à Mailcow.
- **Activer ou désactiver la vérification des entités** : Permet d’activer ou de désactiver la vérification des entités (23h00-05h00; non modifiable).
- **Modification de l'intervalle de la vérification des API** : Offre la possibilité de personnaliser l'intervalle de temps entre chaque vérification des API, afin d'optimiser les performances selon vos besoins (Minutes).

## Installation

1. Assurez-vous que [HACS](https://hacs.xyz) est installé.

2. Ouvrez HACS.
   
3. Cherchez directement : Mailcow HA Custom

ou

3. Cliquez sur les trois points en haut à droite et choisissez "Dépôts personnalisés".

4. Ajoutez le dépôt :
   - URL : 'https://github.com/Master13011/Mailcow-HA'
   - Type : Intégration

5. Cliquez sur "Ajouter".

6. Recherchez "Mailcow HA" dans les intégrations HACS et installez-la.

7. Redémarrez Home Assistant.

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

![{979BA34E-C4AE-4883-AC5A-E22A03D7F318}](https://github.com/user-attachments/assets/5ea7db31-d4be-4402-912a-54bde5f5df3f)

## Contribution

Les contributions à ce projet sont les bienvenues. N'hésitez pas à soumettre des pull requests ou à ouvrir des issues pour des suggestions d'amélioration ou des rapports de bugs.
