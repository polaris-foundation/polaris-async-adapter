Feature: SEND Report PDF
  As a clinician
  I want to generate a PDF report containing a summary of a SEND patient encounter (hospital stay) record
  So that I can review the observations taken

  Background:
    Given a connection to rabbitmq
    And a system JWT
    And a location called "Peaky Blinders Ward" exists
    And the Connector API is up and running
    And the PDF API is up and running
    And the Services API is up and running

  Scenario: Aggregate SEND PDF message (dhos.DM000007) results in SEND PDF being generated
    Given an existing encounter
    And the encounter has observations
    When an aggregate SEND PDF message is published to the broker
    Then a new SEND encounter report PDF has been created
