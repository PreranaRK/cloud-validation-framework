# Open Policy Agent (OPA) Integration

Prancer Cloud Validation framework has built-in simple and robust classic rule engine to write test rules to validate the cloud resources. However with the industry adopting a standard method of writing policy rules and their evaluation, Prancer has integrated OPA (Open Policy Agent) and its rule language (REGO) support to write and evaluate policy rules. By leveraging OPA in Prancer framework, it gives us the capability to write complex rules to evaluate cloud resources.

### Requirements for OPA
  - OPA has been integrated as a binary executable. This executable has to be downloaded and installed with an execute permission.
  - Update prancer config.ini with a separate section as:

```
  [OPA]
  opa=true
  opaexe=<Path to the OPA binary>
```

  - OPA rules can be written embedded in a test case or as a separate rego file. The examples of a classic rule and rego embedded rule in the framework are as:

```
{ 
    "testId": "2",
    "rule":"{TEST_RESOURCE_JSON_ID}.SecurityGroups[0].GroupName='launch-wizard-1'"
},
{
    "testId": "3",
    "type": "rego",
    "rule": "input.SecurityGroups[0].GroupName=\"launch-wizard-1\"",
    "snapshotId": ["TEST_RESOURCE_JSON_ID"],
    "eval": "data.rule.rulepass"
}
```

   The classic rule has an expression with a Left Hand Side(LHS) and Right Hand Side(RHS) with a comparator operator. The classic rule engine evaluates LHS and RHS, uses the comparator to evaluate the rule.

   The Rego rule has an evaluation for a policy and the default has been set to "data.rule.rulepass" and this is evaluated for true value for a test to pass. The rule type has to be specified as "rego" for backward compatability of the framework.

   - *OPA* rules can also be written in a separate rego file. The examples of a classic rule and rego rule written in a separate file in the framework are as:

```
{
    "testId": "1",
    "rule":"exist({TEST_RESOURCE_JSON_ID}.SecurityGroups)"
},
{
    "testId": "4",
    "type": "rego",
    "rule": "file(ruleexists.rego)",
    "snapshotId": ["TEST_RESOURCE_JSON_ID"],
    "eval": "data.rule.rulepass"
}
```

And here is a sample `ruleexists.rego`:
```
package rule
default rulepass = true
rulepass = false{
    is_null(input.SecurityGroups)
}
```

The file ruleexists.rego should exist in the same directory (container) as the test files.

## Examples
Here we are presenting some examples of compliance queries based on the OPA. These examples are based on the `AWS` connector.

### Example 1
This policy identifies the EBS volumes which are not encrypted. The snapshots that you take of an encrypted EBS volume are also encrypted and can be moved between AWS Regions as needed. You cannot share encrypted snapshots with other AWS accounts and you cannot make them public. It is recommended that EBS volume should be encrypted.

Rego rule:
```
package rule
default rulepass = false
rulepass = true{
   input.Volumes[*].Encrypted=false
}
```

### Example 2
EBS volumes often persist after an EC2 instance has been terminated. We recommend regular review of these volumes, since they can contain sensitive data related to your company, application, infrastructure, or even users.

Rego rule:
```
package rule
default rulepass = false
rulepass = true{
   input.Volumes[_].Attachments[_].State!="attached"
}
rulepass = true{
   is_null(input.Volumes[_].Attachments[_])
}"
```

### Example 3
AWS provides Identity Access Management (IAM) roles to securely access AWS services and resources. The role is an identity with permission policies that define what the identity can and cannot do in AWS. As a best practice, create IAM roles and attach the role to manage EC2 instance permissions securely instead of distributing or sharing keys or passwords.

Rego Rule:
```
package rule
default rulepass = false
rulepass = true{
  input.Reservations[_].Instances[_].State.Code=16
  instance := input.Reservations[_].Instances[_]
  not instance.IamInstanceProfile.Arn
}
```

### Example 4
This policy identifies if your account is near the private gateway limitation per VPC per Region. AWS provides a reasonable starting limitation for the maximum number of Virtual private gateways you can assign in each VPC. If you approach the limit in a particular VPC, this alert indicates that you have nearly exhausted your allocation.
NOTE: As per http://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html Virtual private gateway per region limit is 5. This policy will trigger an alert if Virtual private gateway per region reached 80% (i.e. 4) of resource availability limit allocated."

Rego Rule:
```
package rule
default rulepass = false
rulepass = true{
   count(input.VpnGateways)>3
}
```

## References
  - https://www.openpolicyagent.org/docs/latest/  OPA documentation.
  - https://github.com/prancer-io/cloud-validation-framework Prancer command line toolset with OPA


