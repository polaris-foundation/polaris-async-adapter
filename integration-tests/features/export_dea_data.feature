Feature: DEA data export
  As an engineer
  I want anonymised data to be collected
  So that I can monitor and improve my products

  Background:
    Given a connection to rabbitmq
    And a system JWT
    And the DEA Ingest API is up and running
    And the DEA Auth0 tenant is up and running

  Scenario: Export GDM SYNE BG readings message (dhos.DM000015) results in data export to DEA Ingest API
    When an export GDM SYNE BG readings message is published to the broker
    Then the DEA Ingest API has received an export request with data type syne_bg_readings
