Feature: HL7 message processing
  As a clinician
  I want products to be synced with EPR
  So that my patient list is always up to date

  Background:
    Given a connection to rabbitmq
    And a system JWT
    And the Connector API is up and running
    And the Aggregator API is up and running
    And the PDF API is up and running
    And a location called "Orange Ward" exists
    And the Services API is up and running

  Scenario: Patient update (dhos.24891000000101) involving a new admission is processed
    When a patient update message involving a new admission is published to the broker
    Then a new encounter has been created
    And the HL7 message has been marked as processed

  Scenario: Patient update (dhos.24891000000101) involving a discharge is processed
    Given an existing encounter
    When a patient update message involving a discharge is published to the broker
    Then the encounter is marked as discharged
    And the HL7 message has been marked as processed

  Scenario: Patient update (dhos.24891000000101) involving cancellation of an encounter is processed
    Given an existing encounter
    And the encounter has observations
    When a patient update message involving a cancelled admission is published to the broker
    Then the encounter is deleted and merged with a discharged local encounter
    And the HL7 message has been marked as processed

  Scenario: Encounters obs set notification (dhos.DM000004) results in an ORU message
    Given an existing encounter
    When an encounters obs set notification message is published to the broker
    Then an HL7 ORU message is sent

  Scenario Outline: New admission defaults to correct score system
    Given a location set to use a default score system of <default>
    When a patient update message involving a new admission is published to the broker
    Then a new encounter has been created
    And the new encounter has a score system of <score_system>
    And the HL7 message has been marked as processed
    Examples:
      | default | score_system |
      | news2   | news2        |
      | meows   | meows        |
      | NULL    | news2        |
