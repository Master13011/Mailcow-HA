# Mailcow Integration for Home Assistant

This custom integration allows you to connect your Mailcow server to Home Assistant, providing real-time visibility into the status and performance of your email infrastructure.

## Features

- **Mailbox Monitoring**: Displays the total number of mailboxes managed by your Mailcow server.  
- **Domain Tracking**: Shows the number of domains configured on your Mailcow server.  
- **Mailcow Version**: Indicates the current version of your Mailcow installation.  
- **Mailcow Update Check**: Shows whether a new version of your Mailcow installation is available.  
- **Vmail Service Status**: Monitors disk usage for the virtual mail service (Vmail).  
- **Container Status**: Provides an overview of the status of all Docker containers associated with Mailcow.
- **Enable or disable entity verification** : Allows enabling or disabling entity verification, between 11:00 PM and 5:00 AM.
- **Change API check interval**: Customize the time interval between each API check, to optimize performance according to your needs (Minutes).

## Installation

1. Make sure [HACS](https://hacs.xyz) is installed.

2. Open HACS.
   
3. Search : Mailcow HA Custom

or

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

![image](https://github.com/user-attachments/assets/a15a9ce1-fb76-493c-b969-4e1643cdcdfc)

Your instance’s APIs are available here:  
`https://mail.domainmailcow.com/api/#/`

Endpoints used:

```http
GET /api/v1/get/status/containers  
GET /api/v1/get/status/vmail  
GET /api/v1/get/status/version
