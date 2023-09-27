# Planhat Analytics

This page guides you through the process of setting up the Planhat destination connector for general API requests.

Start using Planhat on the [Planhat website](https://www.planhat.com/).

## Overview

The Planhat destination connector supports Append Sync. The connector allows to create and upsert. 

## Prerequisites

Parameters: 
* **Method**
  * CREATE : create an object 
  * UPSERT (bulk): create and update objects. The connector upserts 5000 items per request.
* **Object** The object you want to push into Planhat. See the list above:
  * Asset
  * Campaign
  * Churn
  * Company
  * Conversation
  * Enduser
  * Invoice
  * issue
  * License
  * NPS
  * Opportunity
  * Objective
  * Project
  * Sale
  * Task
  * User
  * Workspace
* **Api Token**  See [this](https://docs.planhat.com/#authentication) to create an api token



## Connector-specific features & highlights

### Input schema 

Planhat needs required parameters depending on the object choosen. Please refer to the [official documentation](https://docs.planhat.com/#planhat_models). If one of the required parameters is missing, the api request will fail.



## Changelog

| Version | Date       | Pull Request                                     | Subject                    |
| :------ | :--------- | :----------------------------------------------- | :------------------------- |
| 0.1.0   | 2023-09-27 | [5](https://github.com/airbytehq/airbyte/pull/5) | 🎉 New Destination: Planhat |
