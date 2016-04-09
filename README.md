# Notification Backend

[![Travis CI](https://img.shields.io/travis/tidycat/notification-backend/master.svg?style=flat-square)](https://travis-ci.org/tidycat/notification-backend)
[![Code Coverage](https://img.shields.io/coveralls/tidycat/notification-backend/master.svg?style=flat-square)](https://coveralls.io/github/tidycat/notification-backend?branch=master)
[![MIT License](https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square)](LICENSE.txt)

This AWS Lambda notification backend will handle the notification and tag portions of Tidy Cat.

**This is very much a work-in-progress**

## Rough Notes

```
- Get all user-specific notifications from that date (defaults to 1 week in the past)
GET /notifications?fromDate=2016-04-08T13:03:43+00:00
GET /notifications

- Get the tags for a specific notification
GET /notifications/1234

- Update the tags for this notification
PATCH /notifications/1234

- Delete a notification
DELETE /notifications/1234

- Populate notifications for the last n months
GET /notifications/refresh

- Get a list of all user-created tags
GET /tags

- Get a specific tag
GET /tags/name

- Update a specific tag
PATCH /tags/name

- Create a new tag
POST /tags

- Delete a tag
DELETE /tags/name
```


## DynamoDB Tables

```
notification
- thread_id (hash)

user-notification
- user_id (hash)
- thread_id (range)
- notification_date (Local secondary index)

tags
- user_id (hash)
- tag_name (range)
```


## Testing Aid

```
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE0NjAyMTk2NTgsImdpdGh1Yl9sb2dpbiI6Im1hcnZpbnBpbnRvIiwic3ViIjoxMTU5OTQyLCJleHAiOjMyNTAzNjgwMDAwLCJnaXRodWJfdG9rZW4iOiJzaGhoIn0.qWGFKUYt5-zgNvV4YygwVAPcZv4NoKH8FaHG_a-xrzg" http://localhost:8080/tags
```
