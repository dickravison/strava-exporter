variable "region" {
  type        = string
  description = "AWS region to deploy the application in"
}

variable "project_name" {
  type        = string
  description = "Name of the project for this application"
}

variable "layer_name" {
  type        = string
  description = "Name of existing lambda layer to use for application dependencies"
}

variable "telegram_chat_id" {
  type        = string
  description = "ID of the telegram chat to post notifications to"
}

variable "telegram_token" {
  type        = string
  description = "Token for the telegram chat to post notifications to"
}

variable "strava_exporter_cron" {
  type        = string
  description = "Cron to determine when to run the Strava exporter"
}

variable "weekly_cron" {
  type        = string
  description = "Cron to determine when to run the weekly stats"
}

variable "monthly_cron" {
  type        = string
  description = "Cron to determine when to run the monthly stats"
}

variable "sns_topic" {
  type        = string
  description = "ARN of the SNS topic to send notifications to"
}

variable "username" {
  type        = string
  description = "Username for eventbridge rules"
}

variable "dynamodb_table_name" {
  type        = string
  description = "Name of the dynamodb table"
}