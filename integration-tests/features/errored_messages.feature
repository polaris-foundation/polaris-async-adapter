Feature: Errored messages
  As an engineer
  I want to badly formed messages to error
  So that I don't have silent failures I can't diagnose

  Background:
    Given a connection to rabbitmq
    And a system JWT

  Scenario Outline: Invalid message causes an error
    When an invalid <routing_key> message is published to the broker
    Then the message goes to the error queue
    Examples:
      | routing_key          |
      | dhos.305058001       |
      | dhos.34837004        |
      | dhos.423779001       |
      | dhos.D9000001        |
      | dhos.D9000002        |
      | dhos.DM000002        |
      | dhos.DM000004        |
      | dhos.DM000005        |
      | dhos.DM000007        |
      | dhos.DM000010        |
      | dhos.DM000015        |
      | gdm.166922008        |
      | dhos.24891000000101  |
      | gdm.424167000        |
