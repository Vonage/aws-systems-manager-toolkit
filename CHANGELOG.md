# Changelog
aws-systems-manager-toolkit Changelog

## [0.0.7] - 2020-08-05
### Bugfix
- ssm-port-forward: Fixed and simplified implementation for the "double" port forwarding to allow multiple connections to the listening local port
- ssm-run: Fixed issue where any invalid instance in the provided list causes exit and doesn't display output of valid instances

## [0.0.6] - 2020-06-18
### Updated
- ssm-list: Added common general parameters for consistency across tools
- ssm-ssh: Added common general parameters for consistency across tools
### Bugfix
- ssm-connect: running sudo su - user upon logging in to source bash profile, redirect user to their own home dir, motd, etc
- ssm-connect/run: use session instatiated by profile/region to create boto3 clients, honors profile/region from user input
- ssm-port-forward: passing in profile and region into the instance id resolver to honor user input
- ssm-port-forward: resolve timing issue between remote tunnel establishment and local to target port forwarding
- ssm-port-forward: print exception when trying to set up global vars
- ssm-run: fixing help message to show correct positional arg placement
- ssm-ssh: Fixed functionality on Windows 64bit/32bit

## [0.0.5] - 2020-05-12
### Bugfix
- ssm-list: changing get_inventory call to describe_instance_information to make sure we avoid displaying offline instances
- ssm-list: fixing ssm-list to handle when an instance doesn't have tags, or is missing a 'name' tag

## [0.0.4] - 2020-04-27
### Bugfix
- ssm-connect: resolve host instance-id based on --region flag

## [0.0.3] - 2020-04-21
### Added
- CHANGELOG.md: Changelog
### Updated
- README.md: Enhancements to the readme
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
