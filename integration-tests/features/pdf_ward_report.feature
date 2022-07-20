Feature: Ward Report PDF
  As a clinician
  I want to generate a PDF containing ward report for patients in a particular location
  So that I can review the statistics on the observations taken

  Background:
    Given a connection to rabbitmq
    And a system JWT
    And the Aggregator API is up and running
    And the PDF API is up and running
    And a location called "Banana Ward" exists
    And the Services API is up and running
    And the DEA Ingest API is up and running
    And the DEA Auth0 tenant is up and running

  Scenario: Generate ward report PDFs message (dhos.DM000010) is consumed
    When an aggregate ward report PDF message is published to the broker
    Then the ward report PDF data is aggregated
    And a new ward report PDF has been created
    And the DEA Ingest API has received an export request with data type ward_report
