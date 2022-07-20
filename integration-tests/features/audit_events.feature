Feature: Audit events
  As a user
  I want to have audit events recorded
  So that I have traceability of key actions

  Background:
    Given a connection to rabbitmq
    And a system JWT

  Scenario: Audit event (dhos.34837004) is consumed
    When an audit event is published to the broker
    Then the event is stored in the Audit API
