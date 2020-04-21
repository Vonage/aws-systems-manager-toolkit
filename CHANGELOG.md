# Changelog
aws-systems-manager-toolkit Changelog

## [0.0.3] - 2020-04-21
### Added
- CHANGELOG.md: Changelog
### Updated
- README.md: Enhancements to the readme
### Removed
- ssm-ssh: Remove create user functionality ssm-ssh will connect as the user specified rather than assumed user
### Bugfix
- ssm-list: handle an instance having no hostname

## [0.0.2] - 2020-04-21
### Added
- create-run-as-user.yml: Document will create a user on a host and add to sudoers file 
- ssm-connect and ssm-ssh will attempt to run the create-run-as-user.yml doc
### Bugfix
- ssm-list: potentially only showing a limited set of instances

## [0.0.1] - 2020-02-25
### Added
- ssm-connect: Connects you to an SSM-enabled machine by InstanceID, Hostname, Name Tag, or IP Address.
- ssm-list: Displays a list of all SSM-enabled machines in the account.
- ssm-port-forward: Simplifies the port forwarding process.
- ssm-run: Quickly run commands on multiple machines at once and see the output broken down by machine.
- ssm-ssh: Delivers the full functionality of SSH, but removes the requirement of using InstanceID's.