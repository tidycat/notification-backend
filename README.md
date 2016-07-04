# Notification Backend

[![Travis CI](https://img.shields.io/travis/tidycat/notification-backend/master.svg?style=flat-square)](https://travis-ci.org/tidycat/notification-backend)
[![Code Coverage](https://img.shields.io/coveralls/tidycat/notification-backend/master.svg?style=flat-square)](https://coveralls.io/github/tidycat/notification-backend?branch=master)
[![MIT License](https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square)](LICENSE.txt)

This AWS-Lambda backend is responsible for the classification and storage of
GitHub notifications.


## Contents

- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
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


## Deployment


#### Create the following DynamoDB table:

- `user-notification`: Primary Key `user_id`, Type `Number`. Sort (range) Key
  `thread_id`, Type `Number`. Secondary Index primary key `user_id` (`Number`),
  sort key `updated_at` (`Number`). Create as a Local Secondary Index.


#### Create an IAM role with a policy that looks something like:

``` json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:*:*:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "dynamodb:*",
            "Resource": [
                "arn:aws:dynamodb:<AWS REGION>:<AWS ACCOUNT ID>:table/user-notification"
            ]
        }
    ]
}
```


#### Create the Lambda function:

- Name: `tidycat-notification-backend`
- Runtime: `Python 2.7`
- Upload zip file: [lambda.zip](https://github.com/tidycat/notification-backend/releases/latest)
- Handler: `notification_backend/entrypoint.handler`
- Role: _IAM role you created earlier_
- Memory: 128 MB
- Timeout: 30 seconds


#### Setup API Gateway:

Create the following API Gateway resources and methods:
``` text
/
  /notification
    /threads
      GET
      /{thread-id}
        GET
        PATCH
        DELETE
    /ping
      GET
```

You will need to run through the following numbered items for _EACH_ of the
methods above:

1. Choose an **Integration type** of _Lambda Function_ and point it at the
   `tidycat-notification-backend` Lambda function.

1. Create the following **Body Mapping Templates** for the method's
   **Integration Request**:

    Content-Type: `application/json`

    ``` json
    {
      "resource-path": "$context.resourcePath",
      "payload": $input.json('$'),
      "http-method": "$context.httpMethod",
      "jwt_signing_secret": "${stageVariables.jwt_signing_secret}",
      "bearer_token": "$input.params().header.get('Authorization')",
      "notification_dynamodb_endpoint_url": "${stageVariables.notification_dynamodb_endpoint_url}",
      "notification_user_notification_dynamodb_table_name": "${stageVariables.notification_user_notification_dynamodb_table_name}",
      "notification_user_notification_date_dynamodb_index_name": "${stageVariables.notification_user_notification_date_dynamodb_index_name}"
    }
    ```

1. Add the following **Method Response** entries, with corresponding **Response
   Models** of `application/json: Empty`.

    - 200
    - 202
    - 400
    - 401
    - 404
    - 409
    - 500

1. Create the following **Integration Response** entries:

    | Lambda Error Regex       | Method response status | Default mapping | BMT Content-Type   | BMT Template                    |
    | ------------------       | ---------------------- | --------------- | ----------------   | ------------                    |
    | _blank_                  | 200                    | Yes             | `application/json` | `$input.json('$.data')`         |
    | `.*"http_status":.202.*` | 202                    | No              | `application/json` | `$input.path('$.errorMessage')` |
    | `.*"http_status":.400.*` | 400                    | No              | `application/json` | `$input.path('$.errorMessage')` |
    | `.*"http_status":.401.*` | 401                    | No              | `application/json` | `$input.path('$.errorMessage')` |
    | `.*"http_status":.404.*` | 404                    | No              | `application/json` | `$input.path('$.errorMessage')` |
    | `.*"http_status":.409.*` | 409                    | No              | `application/json` | `$input.path('$.errorMessage')` |
    | `.*"http_status":.500.*` | 500                    | No              | `application/json` | `$input.path('$.errorMessage')` |

    _Note: BMT = Body Mapping Templates_



Finally, ensure that the following **Stage Variables** are set appropriately:

- `jwt_signing_secret`
- `notification_dynamodb_endpoint_url` (e.g. `https://dynamodb.us-east-1.amazonaws.com`)
- `notification_user_notification_dynamodb_table_name`
- `notification_user_notification_date_dynamodb_index_name`

This will seem cumbersome and thankfully doesn't need to be revisited very
often!


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
