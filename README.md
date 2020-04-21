# aws-systems-manager-toolkit

aws-systems-manager-toolkit is a Python library that provides wrapper tools around AWS Systems Manager functionality.

This project was partially inspired by, and based off of, work done by Michael Ludvig in *[aws-ssm-tools](https://github.com/mludvig/aws-ssm-tools/)*.

All scripts below have been tested with various linux distros, Mac, and Windows10/Server 2019.  

NOTE: On Windows they will install as an .exe file but this still requires a local python installation.

# Requirements

* Python3.x
* AWS CLI


# Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install aws-systems-manager-toolkit.

```bash
pip install aws-systems-manager-toolkit
```

## Tools
* ### ssm-connect

Connects you to an SSM-enabled machine by InstanceID, Hostname, Name Tag, or IP Address. 

If the create-run-as-user.yml doc is uploaded to the account, will also attempt to create the user you're authenticated as, as well as adding you to the sudoers file. The document is located in docs/create-run-as-user.yml. See: *[AWS Documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssm-docs.html)*.

This feature is typically used with the *[Run As](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-preferences-run-as.html)* option enabled in Session Manager preferences.  By enabling this and uploading the document you can now log in as your own username vs the generic ssm-user.  This is often helpful for tracking actions in logs.
    
  usage:
  ```
    ~ $ ssm-connect test-host1

    Starting session with SessionId: session-0d286540f75bc3161
    sh-4.2$
    sh-4.2$ cd
    sh-4.2$ whoami
    ssm-user
    sh-4.2$ hostname
    ip-10-0-0-114.ec2.internal
    sh-4.2$ exit
    exit


    Exiting session with sessionId: session-0d286540f75bc3161.
  ```
* ### ssm-list

Displays a list of all SSM-enabled machines in the account.  You can use any of the results to connect to the system using ssm-connect.

##### Basic usage:
  ```
    ~ $ ssm-list
    i-0a11abcd1ab0abc01   ip-10-0-0-75.ec2.internal    test-host1    10.0.0.75 
    i-0a11abcd1ab0abc02   ip-10-0-0-114.ec2.internal   ssm-test      10.0.0.114
    i-0a11abcd1ab0abc03   ip-10-0-0-55.ec2.internal    test-host2    10.0.0.55 
    i-0a11abcd1ab0abc04   ip-10-0-00-112.ec2.internal  ssm-test2     10.0.0.112

  ```
##### Return instances based on one or more instance tags, using awscli syntax:
  ```
    ~ $ ssm-list --tags Name=tag:Name,Values=test-host1,ssm-test2
    i-0a11abcd1ab0abc01   ip-10-0-0-75.ec2.internal    test-host1    10.0.0.75
    i-0a11abcd1ab0abc04   ip-10-0-00-112.ec2.internal  ssm-test2     10.0.0.112
  ```
* ### ssm-port-forward

Simplifies the port forwarding process.  The following example would expose remote Postgres port 5432 to your localhost:12345.  

  usage:
  ```
    ~ $ ssm-port-forward --target i-0a11abcd1ab0abc01:5432 --local 12345

    Starting session with SessionId: session-07cb202eeca63c39d
    Port 12345 opened for sessionId session-07cb202eeca63c39d.
        
    ^CTerminate signal received, exiting.


    Exiting session with sessionId: session-07cb202eeca63c39d.
  ```
  
  #### You can also double port forward (set up port forwarding on the remote host first)
  
This is useful in situations where you have a database like RDS that is not running SSM.  Behind the scenes the script will setup 2 tunnels.  
  
  1) A tunnel from your machine -> jumphost
  2) A tunnel from jumphost -> RDS

In order to create the second tunnel we create a temporary user and pem on the jump host.  When you CTRL+C and end the script the user is also removed.  
  
NOTE: In situations where internet is lost the temporary user can be left behind.  The user has a unique hash in the username in order to not conflict with regular OS users.  
  
  usage:
  ```
            
    ~ $ ssm-port-forward --target i-0d14faab9db41ee57:3389 --local 12345 --remote i-0a11abcd1ab0abc01:111

    Starting session with SessionId: user-0c702acdf8f164b7a
    Port 12345 opened for sessionId user-0c702acdf8f164b7a.

    ^CTerminate signal received, exiting.
    Stopping remote SSH tunnel with Command ID 18bf6db1-7a2b-44bc-901a-ffc07c1868a1


    Exiting session with sessionId: user-0c702acdf8f164b7a.
  ```
* ### ssm-run

Quickly run commands on multiple machines at once and see the output broken down by machine. 

  usage:
  ```
    ~ $ ssm-run 10.0.0.114 10.0.0.55 --commands whoami hostname pwd "sudo cat /etc/redhat-release"
    10.0.0.114 | i-0a11abcd1ab0abc01
    root
    ip-10-0-0-114.ec2.internal
    /usr/bin
    CentOS Linux release 7.7.1908 (Core)

    10.0.0.55 | i-0a11abcd1ab0abc01
    root
    ip-10-0-0-55.ec2.internal
    /usr/bin
    CentOS Linux release 7.7.1908 (Core)
  
  ```
* ### ssm-ssh

Delivers the full functionality of SSH, but removes the requirement of using InstanceID's.  Connect to any machine by using the same results provided by ssm-list.

  usage:
  ```
    ~ $ ssm-ssh -i ~/.ssh/myuser.pem  myuser@10.0.0.114
    Last login: Mon Feb 24 18:39:45 2020 from localhost

    [myuser@ip-10-0-0-114 ~]$ exit
    logout
    Connection to i-0a11abcd1ab0abc01 closed.
  
  ```
## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.


## License
[MIT](https://choosealicense.com/licenses/mit/)
