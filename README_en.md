# Mailcow Integration for Home Assistant

This custom integration allows you to connect your Mailcow server to Home Assistant, providing real-time visibility into the status and performance of your email infrastructure.

## Features

- **Mailbox Monitoring**: Displays the total number of mailboxes managed by your Mailcow server.  
- **Domain Tracking**: Shows the number of domains configured on your Mailcow server.  
- **Mailcow Version**: Indicates the current version of your Mailcow installation.  
- **Mailcow Update Check**: Shows whether a new version of your Mailcow installation is available.  
- **Vmail Service Status**: Monitors disk usage for the virtual mail service (Vmail).  
- **Container Status**: Provides an overview of the status of all Docker containers associated with Mailcow.
- **Intelligent Caching** 🧠: All sensor data is cached locally for 12 hours to reduce load on the Mailcow API and improve Home Assistant performance.

## Installation

1. Make sure [HACS](https://hacs.xyz) is installed.

2. Open HACS.

3. Click the three dots in the top right corner and choose "Custom repositories".

4. Add the repository:  
   - **URL**: `https://github.com/Master13011/Mailcow-HA`  
   - **Type**: Integration

5. Click "Add".

6. Search for **Mailcow HA** in HACS integrations and install it.

7. Restart Home Assistant.

## Configuration

From your Mailcow Admin Interface:  
`https://mail.domainmailcow.com/admin`, enable the API.

![image](https://github.com/user-attachments/assets/8ecac93c-2acd-457d-8170-57b99ddb9257)

Your instance’s APIs are available here:  
`https://mail.domainmailcow.com/api/#/`

Endpoints used:

```http
GET /api/v1/get/status/containers  
GET /api/v1/get/status/vmail  
GET /api/v1/get/status/version  
