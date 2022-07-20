Feature: Activation and authentication
  As a user
  I want to be able to log in to SEND Entry
  So that I can look after my patients

  Background:
    Given a connection to rabbitmq
    And a SEND device JWT

  Scenario: Create activation auth clinician message (dhos.D9000001) is consumed
    When a create activation auth clinician message is published to the broker
    Then the clinician can get a JWT from Activation Auth API
