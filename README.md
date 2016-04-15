# Notification Backend

[![Travis CI](https://img.shields.io/travis/tidycat/notification-backend/master.svg?style=flat-square)](https://travis-ci.org/tidycat/notification-backend)
[![Code Coverage](https://img.shields.io/coveralls/tidycat/notification-backend/master.svg?style=flat-square)](https://coveralls.io/github/tidycat/notification-backend?branch=master)
[![MIT License](https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square)](LICENSE.txt)

This AWS Lambda notification backend will handle the notification and tag portions of Tidy Cat.

**This is very much a work-in-progress**



## Contents

- [Features](#features)
- [Overview](#overview)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Development](#development)


## Features

- `[WIP]`


## Overview

- `[WIP]`


## API Endpoints

| Endpoint | HTTP Verb | Task |
| -------- | --------- | ---- |
| `/notification/threads` | `GET` | Optionally with the `fromDate` parameter (e.g.  `fromDate=2016-04-08T13:03:43+00:00`). Return a list of all relevant notifications starting from `fromDate`. Defaults to one week in the past. |
| `/notification/threads/1234` | `GET` | Return all the information relevant to notification id `1234`. |
| `/notification/threads/1234` | `PATCH` | Update the information pertinent to notification id `1234`. |
| `/notification/threads/1234` | `DELETE` | Delete notification id `1234`. |
| `/notification/threads/refresh` | `POST` | Populate the user's notifications for the last `n` months. |
| `/notification/tags` | `GET` | Return a list of all the user-created tags. |
| `/notification/tags/name` | `GET` | Return all the information relevant to tag `name`. |
| `/notification/tags/name` | `PATCH` | Update the information pertinent to tag `name`. |
| `/notification/tags` | `POST` | Create a new tag. |
| `/notification/tags/name` | `DELETE` | Delete tag `name`. |


## Deployment


#### Create the DynamoDB tables:

- `notification`: Primary Key `thread_id`, Type `Number`.

- `user-notification`: Primary Key `user_id`, Type `Number`. Sort (range) Key
  `thread_id`, Type `Number`. Secondary Index primary key `user_id` (`Number`),
  sort key `notification_date` (`Number`). Create as a Local Secondary Index.

- `tags`: Primary Key `user_id`, Type `Number`. Sort Key `tag_name`, Type
  `String`.


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
                "logs:PutLogEvents",
                "sns:Publish",
                "sns:Subscribe"
            ],
            "Resource": [
                "arn:aws:logs:*:*:*",
                "arn:aws:sns:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "dynamodb:*",
            "Resource": [
                "arn:aws:dynamodb:<AWS REGION>:<AWS ACCOUNT ID>:table/notification",
                "arn:aws:dynamodb:<AWS REGION>:<AWS ACCOUNT ID>:table/user-notification",
                "arn:aws:dynamodb:<AWS REGION>:<AWS ACCOUNT ID>:table/tags"
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


## Development

- `[WIP]`

```
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE0NjAyMTk2NTgsImdpdGh1Yl9sb2dpbiI6Im1hcnZpbnBpbnRvIiwic3ViIjoxMTU5OTQyLCJleHAiOjMyNTAzNjgwMDAwLCJnaXRodWJfdG9rZW4iOiJzaGhoIn0.qWGFKUYt5-zgNvV4YygwVAPcZv4NoKH8FaHG_a-xrzg" http://localhost:8080/tags
```
