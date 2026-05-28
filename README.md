# MySQL Test Application
[![Charmhub Badge](https://charmhub.io/mysql-test-app/badge.svg)](https://charmhub.io/mysql-test-app)
[![Release](https://github.com/canonical/mysql-test-app/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/mysql-test-app/actions/workflows/release.yaml)
[![Tests](https://github.com/canonical/mysql-test-app/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/canonical/mysql-test-app/actions/workflows/ci.yaml)

MySQL test charm - is a simple application used exclusively for various tests of
various tests of "Charmed MySQL" charms (see the "References" section).

## Relations
This charm implements [relations interfaces](https://charmhub.io/mysql-k8s/docs/e-interfaces):
* database
* mysql (legacy)

The list of available endpoints is [here](https://charmhub.io/mysql-test-app/integrations).

On using the `mysql` legacy relation interface with either [mysql] or [mysql-k8s] charms, its
necessary to config the database name with:

```shell
> juju config mysql-k8s mysql-interface-database=continuous_writes
```

## Actions
Actions are listed on [actions page](https://charmhub.io/mysql-test-app/actions)

## References
* [MySQL Test App](https://charmhub.io/mysql-test-app)
* [mysql](https://charmhub.io/mysql)
* [mysql-k8s](https://charmhub.io/mysql-k8s)
* [mysql-router](https://charmhub.io/mysql-router)
* [mysql-router-k8s](https://charmhub.io/mysql-router-k8s)

## Security
Security issues in the MySQL Test App can be reported through [LaunchPad](https://wiki.ubuntu.com/DebuggingSecurity#How%20to%20File). Please do not file GitHub issues about security issues.

## Contributing
Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this charm following best practice guidelines, and [CONTRIBUTING.md](https://github.com/canonical/mysql-test-app/blob/main/CONTRIBUTING.md) for developer guidance.

## License
The MySQL Test App [is distributed](https://github.com/canonical/mysql-test-app/blob/main/LICENSE) under the Apache Software License, version 2.0.
It installs/operates/depends on [MySQL Community Edition](https://github.com/mysql/mysql-server), which [is licensed](https://github.com/mysql/mysql-server/blob/8.0/LICENSE) under the GPL License, version 2.

## Trademark Notice
MySQL is a trademark or registered trademark of Oracle America, Inc.
Other trademarks are property of their respective owners.
