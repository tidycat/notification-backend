# Notification Backend

[![Travis CI](https://img.shields.io/travis/tidycat/notification-backend/master.svg?style=flat-square)](https://travis-ci.org/tidycat/notification-backend)
[![Code Coverage](https://img.shields.io/coveralls/tidycat/notification-backend/master.svg?style=flat-square)](https://coveralls.io/github/tidycat/notification-backend?branch=master)
[![MIT License](https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square)](LICENSE.txt)

This AWS-Lambda backend is responsible for the classification and storage of
GitHub notifications.


## Contents

- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Development](#development)


## Features

- Conforms to the [JSON API](http://jsonapi.org) specification.


## API Endpoints

| Endpoint | HTTP Verb | Task |
| -------- | --------- | ---- |
| `/notification/threads` | `GET` | Optionally with the `from` parameter (e.g.  `from=<epoch seconds>`). Return a list of all relevant notifications starting from `from`. Defaults to one week in the past. |
| `/notification/threads/1234` | `GET` | Return all the information relevant to notification id `1234`. |
| `/notification/threads/1234` | `PATCH` | Update the information pertinent to notification id `1234`. |
| `/notification/threads/1234` | `DELETE` | Delete notification id `1234`. |
| `/notification/ping` | `GET` | Return the currently running version of the Lambda function. |


## Development

#### Tools

- Python 2.7.11 (AWS Lambda needs 2.7.x)
- Java runtime 6.x or newer (for the local DynamoDB instance)

#### Environment Variables

- `DYNAMODB_ENDPOINT_URL` (e.g. `http://localhost:8000`)
- `NOTIFICATION_USER_NOTIFICATION_DYNAMODB_TABLE_NAME` (e.g. `user-notification`)
- `NOTIFICATION_USER_NOTIFICATION_DATE_DYNAMODB_INDEX_NAME` (e.g. `user-notification-date`)

#### Workflow

First and foremost, have a read through all the targets in the Makefile. I've
opted for the [self-documentation][1] approach so issue a `make` and have a
look at all your options.

You can run the local test server while developing instead of deploying to AWS
and testing there (`make server`). If you need to re-initialize the local
DynamoDB instance, first run `make local-dynamodb` and after that is up and
running, `make init-local-dynamodb` (in another terminal window).

That should give you a pretty decent local environment to develop in!

[Bug reports][2] or [contributions][3] are always welcome.


[1]: http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
[2]: https://github.com/tidycat/notification-backend/issues
[3]: https://github.com/tidycat/notification-backend/pulls
