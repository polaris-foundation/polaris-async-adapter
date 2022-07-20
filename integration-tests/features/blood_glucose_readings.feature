Feature: Blood glucose readings
  As a user
  I want to have alerts on blood glucose readings
  So that I can see which patients need attention

  Background:
    Given a connection to rabbitmq
    And a system JWT
    And a location called "Apple Ward" exists
    And the Services API is up and running
    And the Trustomer API is up and running

  Scenario: Abnormal BG reading message (gdm.166922008) is consumed
    Given a patient has a recent abnormal BG reading
    When the patient records another abnormal BG reading
    Then the reading results in an amber alert
    And a new glucose alert message has been created
